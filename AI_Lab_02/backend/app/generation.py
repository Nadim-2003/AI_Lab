"""Reproducible, explicitly simulated Dhaka scenarios; no external data required."""

import random
from collections import Counter
from .models import Generate, Requirement, Incident, Resource, Hospital, Road, Scenario
from .routing import distance

ROLES = ["ambulance", "fire", "rescue"]
CENTERS = [
    ("S1", "Dhanmondi", "2:1"),
    ("S2", "Mirpur", "0:3"),
    ("S3", "Gulshan", "2:7"),
    ("S4", "Motijheel", "6:6"),
    ("S5", "Dhaka University", "6:3"),
]


def demands(category, severity, rules=None):
    if rules and category in rules:
        return [q.model_copy(deep=True) for q in rules[category]]
    ambulance = Requirement(role="ambulance", patients=1, capabilities=["medical"])
    rescue = Requirement(role="rescue", capacity=4, capabilities=["rescue"])
    fire = Requirement(role="fire", capacity=4, capabilities=["firefighting"])
    if category == "medical":
        return [ambulance]
    if category == "fire":
        return [fire, ambulance] + ([rescue] if severity >= 4 else [])
    if category == "accident":
        return [ambulance, rescue]
    if category == "flood":
        return [rescue] + ([ambulance] if severity >= 4 else [])
    raise ValueError("Supply a demand rule for a custom incident category")


def generate(config: Generate):
    if config.demo == "backjumping":
        return backjumping_scenario()
    rng = random.Random(config.seed)
    nodes = {
        f"{r}:{c}": (90.32 + c * 0.018, 23.86 - r * 0.018)
        for r in range(9)
        for c in range(9)
    }
    roads = []
    for r in range(9):
        for c in range(9):
            for dr, dc in [(0, 1), (1, 0)]:
                if r + dr >= 9 or c + dc >= 9:
                    continue
                u, v = f"{r}:{c}", f"{r+dr}:{c+dc}"
                blocked = rng.random() < config.block_fraction
                traffic = rng.uniform(1, 2.2)
                for a, b in [(u, v), (v, u)]:
                    roads.append(
                        Road(
                            id=f"{a}>{b}",
                            u=a,
                            v=b,
                            distance_km=distance(nodes[a], nodes[b]),
                            speed_kph=25,
                            traffic=traffic,
                            blocked=blocked,
                        )
                    )
    count = (
        1
        if config.demo in ["medical", "fire", "blocked"]
        else (3 if config.demo in ["competition", "insufficient"] else config.count)
    )
    categories = (
        list(config.rules) if config.rules else ["medical", "fire", "accident", "flood"]
    )
    if not categories:
        raise ValueError("Demand rules cannot be empty")
    incidents = []
    for n in range(count):
        category = rng.choice(categories)
        if config.demo in ["medical", "blocked", "competition", "insufficient"]:
            category = "medical"
        if config.demo == "fire":
            category = "fire"
        severity = rng.randint(1, 5)
        node = rng.choice(list(nodes))
        deadline = config.deadline * (
            {1: 1, 2: 1, 3: 0.8, 4: 0.65, 5: 0.5}[severity]
            if config.severity_deadlines
            else 1
        )
        incidents.append(
            Incident(
                id=f"I{n+1:03}",
                category=category,
                node=node,
                severity=severity,
                deadline=deadline,
                requirements=demands(category, severity, config.rules),
            )
        )
    needed = Counter()
    patients = 0
    for i in incidents:
        for q in i.requirements:
            needed[q.role] += q.quantity
            patients += q.patients * q.quantity
    resources = []
    for role, total in sorted(needed.items()):
        factor = (
            config.ambulance_factor
            if role == "ambulance"
            else config.rescue_factor if role == "rescue" else 1
        )
        amount = round(total * config.supply * factor)
        if config.demo in ["competition", "insufficient"]:
            amount = 1
        for n in range(amount):
            sid, _, node = CENTERS[n % len(CENTERS)]
            busy = role == "fire" and n < int(amount * config.fire_busy_fraction)
            resources.append(
                Resource(
                    id=f"{role.upper()}-{n+1:03}",
                    role=role,
                    station=sid,
                    home_node=node,
                    node=node,
                    capacity=4 if role != "ambulance" else 2,
                    capabilities=[
                        {
                            "ambulance": "medical",
                            "fire": "firefighting",
                            "rescue": "rescue",
                        }.get(role, role)
                    ],
                    available=not busy,
                    release_at=120 if busy else 0,
                    dispatch_cost={"ambulance": 500, "fire": 1100, "rescue": 700}.get(
                        role, 700
                    ),
                )
            )
    beds = round(patients * config.hospital_factor)
    hospitals = [
        Hospital(
            id=f"H{n+1}",
            name=name + " simulated hospital",
            node=node,
            beds=beds // 3 + (n < beds % 3),
            capabilities=["emergency", "trauma"],
        )
        for n, (name, node) in enumerate(
            [("Central", "5:3"), ("North", "1:4"), ("East", "4:7")]
        )
    ]
    if config.demo in ["medical", "fire", "blocked"]:
        # Small understandable demonstrations have sufficient dispatch supply.
        for resource in resources:
            resource.node = resource.home_node = "6:3"
            resource.station = "S5"
        incidents[0].node = "6:5"
        if config.demo == "blocked":
            for edge in roads:
                if {edge.u, edge.v} == {"6:3", "6:4"}:
                    edge.blocked = True
    budget = sum(r.dispatch_cost + 700 for r in resources) * config.budget_factor
    return Scenario(
        seed=config.seed,
        nodes=nodes,
        roads=roads,
        incidents=incidents,
        resources=resources,
        hospitals=hospitals,
        stations=[
            {"id": sid, "name": name + " simulated center", "node": node}
            for sid, name, node in CENTERS
        ],
        budget=budget,
    )


def backjumping_scenario():
    """Real resource-slot witness: A conflicts with C; B is unrelated."""
    nodes = {"a": (90.39, 23.73), "b": (90.40, 23.73), "c": (90.41, 23.73)}
    roads = [
        Road(id=f"{u}>{v}", u=u, v=v, distance_km=1, speed_kph=30)
        for u, v in [("a", "b"), ("b", "a"), ("b", "c"), ("c", "b")]
    ]
    resources = [
        Resource(id=rid, role=role, station=station, home_node=node, node=node)
        for rid, role, station, node in [
            ("AM1", "ambulance", "S1", "a"),
            ("AM2", "ambulance", "S2", "c"),
            ("RT1", "rescue", "S1", "a"),
            ("RT2", "rescue", "S2", "c"),
        ]
    ]
    incidents = [
        Incident(
            id="A",
            category="medical",
            node="b",
            requirements=[Requirement(role="ambulance")],
        ),
        Incident(
            id="B",
            category="flood",
            node="b",
            requirements=[Requirement(role="rescue")],
        ),
        Incident(
            id="C",
            category="medical",
            node="a",
            deadline=1,
            requirements=[Requirement(role="ambulance")],
        ),
    ]
    return Scenario(
        name="CBJ witness: on-scene medical care, no patient transport",
        nodes=nodes,
        roads=roads,
        resources=resources,
        hospitals=[],
        incidents=incidents,
        stations=[
            {"id": "S1", "name": "West simulated center", "node": "a"},
            {"id": "S2", "name": "East simulated center", "node": "c"},
        ],
        budget=10000,
    )
