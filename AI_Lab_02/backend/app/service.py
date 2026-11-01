from collections import Counter
from time import perf_counter
from .problem import Problem
from .solvers import run
from .validation import validate


def solve(scenario, options, problem=None):
    began = perf_counter()
    p = problem if problem is not None else Problem(scenario)
    preparation_ms = (perf_counter() - began) * 1000
    assignment, status, metrics, failures, trace, raw = run(p, options)
    checked = validate(p, assignment)
    if not checked["valid"]:
        raise RuntimeError(
            "Solver returned invalid allocation: " + str(checked["violations"])
        )
    if checked["complete"]:
        status = "feasible"
    rows = []
    counts = Counter()
    for incident in scenario.incidents:
        slots = [x for x in p.slots if p.slots[x].incident.id == incident.id]
        assigned = [x for x in slots if x in assignment]
        state = (
            "fully_served"
            if len(assigned) == len(slots)
            else "partially_served" if assigned else "unserved"
        )
        counts[state] += 1
        reasons = {}
        for x in slots:
            if x in assignment:
                continue
            if not p.domains[x]:
                reasons[x] = {
                    "empty_domain": True,
                    "excluded_candidates": p.rejections[x],
                }
            else:
                p.prepare(assignment)
                codes = Counter()
                for v in p.domains[x]:
                    _, violated = p.conflicts(x, v, assignment)
                    codes.update(violated)
                reasons[x] = {
                    "candidate_count": len(p.domains[x]),
                    "conflicts_with_returned_subset": dict(codes),
                    "note": "Search limit or earlier choices can leave feasible slots unassigned; subset is not proven maximum.",
                }
        rows.append(
            {
                "id": incident.id,
                "status": state,
                "assigned": len(assigned),
                "required": len(slots),
                "unmet": reasons,
            }
        )
    allocated = []
    for x, v in assignment.items():
        i = p.slots[x].incident
        transport_minutes = v.transport["minutes"] if v.transport else 0
        allocated.append(
            {
                "slot": x,
                "incident": i.id,
                "role": p.slots[x].requirement.role,
                "resource": v.resource,
                "station": p.resources[v.resource].station,
                "hospital": v.hospital,
                "patients": v.patients,
                "response": v.response,
                "transport": v.transport,
                "eta_minutes": v.response["minutes"],
                "arrival_at": i.requested_at + v.response["minutes"],
                "release_at": i.requested_at
                + v.response["minutes"]
                + i.service_minutes
                + transport_minutes,
                "transport_minutes": transport_minutes,
                "cost": v.cost,
            }
        )
    return {
        "status": status,
        "algorithm": options.algorithm,
        "options": options.model_dump(),
        "optimal": False,
        "summary": {
            **{
                key: counts[key]
                for key in ["fully_served", "partially_served", "unserved"]
            },
            "allocated_units": len(assignment),
            "required_slots": len(p.slots),
        },
        "assignments": allocated,
        "incidents": rows,
        "metrics": metrics,
        "validation": checked,
        "constraint_failures": failures,
        "domain_rejections": dict(
            sum((Counter(v) for v in p.rejections.values()), Counter())
        ),
        "empty_domains": [x for x, d in p.domains.items() if not d],
        "trace": trace,
        "local_unresolved": raw,
        "preparation_ms": preparation_ms,
    }
