from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Requirement(Model):
    role: str = Field(min_length=1, max_length=40)
    quantity: int = Field(1, ge=1, le=5)
    capacity: int = Field(1, ge=1, le=100)
    capabilities: list[str] = Field(default_factory=list, max_length=20)
    patients: int = Field(0, ge=0, le=20)
    hospital_capability: str = "emergency"

    @model_validator(mode="after")
    def patient_transport(self):
        if self.patients and self.role != "ambulance":
            raise ValueError("Patient transport slots must require an ambulance")
        return self


class Incident(Model):
    id: str
    category: str
    node: str
    severity: int = Field(3, ge=1, le=5)
    requirements: list[Requirement] = Field(min_length=1, max_length=8)
    requested_at: float = Field(0, ge=0, le=10000)
    deadline: float = Field(60, gt=0, le=10000)
    service_minutes: float = Field(15, ge=0, le=1000)
    status: str = "pending"


class Resource(Model):
    id: str
    role: str
    station: str
    home_node: str
    node: str
    available: bool = True
    release_at: float = Field(0, ge=0)
    capabilities: list[str] = Field(default_factory=list)
    capacity: int = Field(4, ge=1, le=100)
    dispatch_cost: float = Field(500, ge=0, le=1000000)
    cost_per_km: float = Field(30, ge=0, le=100000)


class Hospital(Model):
    id: str
    name: str
    node: str
    beds: int = Field(10, ge=0, le=100000)
    capabilities: list[str] = Field(default_factory=lambda: ["emergency"])


class Station(Model):
    id: str
    name: str
    node: str


class Road(Model):
    id: str
    u: str
    v: str
    distance_km: float = Field(gt=0, le=1000)
    speed_kph: float = Field(25, gt=0, le=200)
    traffic: float = Field(1, ge=1, le=10)
    blocked: bool = False


class Scenario(Model):
    name: str = "Dhaka simulated dispatch"
    seed: int = 42
    nodes: dict[str, tuple[float, float]] = Field(min_length=1, max_length=2000)
    roads: list[Road] = Field(max_length=10000)
    stations: list[Station] = Field(default_factory=list, max_length=50)
    hospitals: list[Hospital] = Field(max_length=50)
    resources: list[Resource] = Field(max_length=2000)
    incidents: list[Incident] = Field(min_length=1, max_length=300)
    budget: float = Field(1000000, ge=0, le=1000000000)
    source: str = (
        "Simulated Dhaka geography, roads, traffic, stations, hospitals and operations; not real dispatch data."
    )

    @model_validator(mode="after")
    def references(self):
        for items in [
            self.resources,
            self.incidents,
            self.hospitals,
            self.roads,
            self.stations,
        ]:
            ids = [x.id for x in items]
            if len(set(ids)) != len(ids):
                raise ValueError("IDs must be unique within each collection")
        for road in self.roads:
            if road.u not in self.nodes or road.v not in self.nodes:
                raise ValueError("Unknown road endpoint")
        for item in [*self.incidents, *self.resources, *self.hospitals, *self.stations]:
            if item.node not in self.nodes:
                raise ValueError("Unknown current node")
        centers = {station.id: station for station in self.stations}
        if centers and any(
            r.station not in centers or r.home_node != centers[r.station].node
            for r in self.resources
        ):
            raise ValueError("Resource home node must match its declared station")
        if any(r.home_node not in self.nodes for r in self.resources):
            raise ValueError("Unknown home node")
        if sum(q.quantity for i in self.incidents for q in i.requirements) > 900:
            raise ValueError("At most 900 resource slots per scenario")
        for lon, lat in self.nodes.values():
            if not (89 <= lon <= 92 and 22 <= lat <= 25):
                raise ValueError("Node coordinates must be in the Dhaka region")
        return self


class Generate(Model):
    count: int = Field(10, ge=1, le=300)
    seed: int = Field(42, ge=0, le=1000000)
    deadline: float = Field(60, gt=0, le=240)
    severity_deadlines: bool = False
    supply: float = Field(1.05, ge=0, le=2)
    ambulance_factor: float = Field(1, ge=0, le=2)
    rescue_factor: float = Field(1, ge=0, le=2)
    fire_busy_fraction: float = Field(0, ge=0, le=1)
    hospital_factor: float = Field(1.1, ge=0, le=2)
    budget_factor: float = Field(1.3, ge=0, le=3)
    block_fraction: float = Field(0.04, ge=0, le=0.8)
    demo: Literal[
        "custom",
        "medical",
        "fire",
        "competition",
        "blocked",
        "insufficient",
        "backjumping",
    ] = "custom"
    rules: dict[str, list[Requirement]] | None = None


class Options(Model):
    algorithm: Literal[
        "backtracking",
        "backjumping",
        "forward_checking",
        "arc_consistency",
        "local_search",
    ] = "backtracking"
    mrv: bool = True
    degree: bool = True
    lcv: bool = False
    severity_order: bool = True
    mac: bool = False
    max_steps: int = Field(10000, ge=1, le=200000)
    timeout: float = Field(3, gt=0, le=15)
    seed: int = 42
    restarts: int = Field(2, ge=0, le=10)


class SolveRequest(Model):
    scenario: Scenario
    options: Options = Field(default_factory=Options)


class CompareRequest(Model):
    scenario: Scenario
    options: list[Options] = Field(min_length=1, max_length=8)


class Experiment(Model):
    kind: Literal["scale", "deadline", "pressure"] = "deadline"
    generation: Generate = Field(default_factory=Generate)
    options: list[Options] = Field(
        default_factory=lambda: [
            Options(timeout=2),
            Options(algorithm="backjumping", timeout=2),
            Options(algorithm="forward_checking", timeout=2),
            Options(algorithm="arc_consistency", timeout=2),
            Options(algorithm="local_search", timeout=2),
        ],
        max_length=8,
        min_length=1,
    )
    sizes: list[int] = Field(
        default_factory=lambda: [10, 20, 30, 50, 100, 150, 250, 300],
        min_length=1,
        max_length=8,
    )
    repeats: int = Field(1, ge=1, le=3)

    @model_validator(mode="after")
    def limits(self):
        if any(n < 1 or n > 300 for n in self.sizes):
            raise ValueError("Sizes must be 1..300")
        if any(o.timeout > 2 or o.max_steps > 10000 for o in self.options):
            raise ValueError("Batch runs require timeout <= 2s and max_steps <= 10000")
        return self
