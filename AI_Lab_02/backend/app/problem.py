from collections import Counter
from dataclasses import dataclass
from .routing import Router


@dataclass(frozen=True)
class Slot:
    id: str
    incident: object
    requirement: object


@dataclass(frozen=True)
class Value:
    resource: str
    hospital: str | None
    response: dict
    transport: dict | None
    cost: float
    patients: int


class Problem:
    def __init__(self, scenario):
        self.scenario = scenario
        self.resources = {r.id: r for r in scenario.resources}
        self.hospitals = {h.id: h for h in scenario.hospitals}
        self.router = Router(scenario)
        self.slots, self.domains, self.rejections = {}, {}, {}
        for incident in scenario.incidents:
            for qi, req in enumerate(incident.requirements):
                for k in range(req.quantity):
                    name = f"{incident.id}/{qi}/{k}"
                    self.slots[name] = Slot(name, incident, req)
                    values, reasons = [], Counter()
                    for resource in scenario.resources:
                        if resource.role != req.role:
                            reasons["C1_type"] += 1
                            continue
                        if (
                            not resource.available
                            or resource.release_at > incident.requested_at
                        ):
                            reasons["C2_availability"] += 1
                            continue
                        if resource.capacity < max(
                            req.capacity, req.patients
                        ) or not set(req.capabilities) <= set(resource.capabilities):
                            reasons["C6_capacity_capability"] += 1
                            continue
                        response = self.router.route(resource.node, incident.node)
                        if response is None:
                            reasons["C5_C8_unreachable"] += 1
                            continue
                        if response["minutes"] > incident.deadline:
                            reasons["C4_deadline"] += 1
                            continue
                        choices = [(None, None)] if not req.patients else []
                        if req.patients:
                            for h in scenario.hospitals:
                                transport = self.router.route(incident.node, h.node)
                                if (
                                    h.beds >= req.patients
                                    and req.hospital_capability in h.capabilities
                                    and transport is not None
                                ):
                                    choices.append((h.id, transport))
                            if not choices:
                                reasons["C10_hospital"] += 1
                        for hospital, transport in choices:
                            km = response["distance_km"] + (
                                transport["distance_km"] if transport else 0
                            )
                            cost = resource.dispatch_cost + resource.cost_per_km * km
                            if cost > scenario.budget:
                                reasons["C7_budget"] += 1
                                continue
                            values.append(
                                Value(
                                    resource.id,
                                    hospital,
                                    response,
                                    transport,
                                    cost,
                                    req.patients,
                                )
                            )
                    self.domains[name] = values
                    self.rejections[name] = dict(reasons)
        # Inverted indices avoid an expensive all-domain-pairs graph construction.
        groups = {}
        for x, domain in self.domains.items():
            for key in {("r", v.resource) for v in domain} | {
                ("h", v.hospital) for v in domain if v.hospital
            }:
                groups.setdefault(key, set()).add(x)
        self.neighbors = {x: set() for x in self.slots}
        for group in groups.values():
            for x in group:
                self.neighbors[x].update(group - {x})

    def compatible(self, x, a, y, b):
        if a.resource == b.resource:
            return False
        if a.hospital and a.hospital == b.hospital:
            return a.patients + b.patients <= self.hospitals[a.hospital].beds
        return True

    def prepare(self, assignment):
        self._assignment = assignment
        self._used = {}
        self._beds = Counter()
        self._cost = 0
        for x, v in assignment.items():
            self._used.setdefault(v.resource, set()).add(x)
            self._cost += v.cost
            if v.hospital:
                self._beds[v.hospital] += v.patients

    def conflicts(self, x, value, assignment):
        if getattr(self, "_assignment", None) is not assignment:
            self.prepare(assignment)
        old = assignment.get(x)
        causes = set(self._used.get(value.resource, set())) - {x}
        codes = {"C3_exclusivity"} if causes else set()
        if (
            value.cost + self._cost - (old.cost if old else 0)
            > self.scenario.budget + 1e-7
        ):
            causes.update(set(assignment) - {x})
            codes.add("C7_budget")
        beds = self._beds[value.hospital] - (
            old.patients if old and old.hospital == value.hospital else 0
        )
        if (
            value.hospital
            and beds + value.patients > self.hospitals[value.hospital].beds
        ):
            causes.update(
                y
                for y, v in assignment.items()
                if y != x and v.hospital == value.hospital
            )
            codes.add("C10_hospital_beds")
        return causes, codes
