"""Independent final validator: recomputes routes/costs, does not trust domains."""

from collections import Counter
from math import isclose


def validate(problem, assignment, require_complete=False):
    s = problem.scenario
    errors = []
    used = Counter()
    beds = Counter()
    cost = 0

    def error(code, slot):
        errors.append({"constraint": code, "slot": slot})

    def route_check(route, origin, target, x):
        if route is None:
            error("C5_C8_route_missing", x)
            return 0, 0
        u = origin
        minutes = 0
        km = 0
        nodes = [origin]
        for eid in route.get("edges", []):
            edge = problem.router.roads.get(eid)
            if edge is None or edge.blocked or edge.u != u:
                error("C5_C8_invalid_road", x)
                return 0, 0
            u = edge.v
            nodes.append(u)
            km += edge.distance_km
            minutes += edge.distance_km / edge.speed_kph * 60 * edge.traffic
        if (
            u != target
            or route.get("origin") != origin
            or route.get("destination") != target
            or route.get("nodes") != nodes
        ):
            error("C8_route_endpoints", x)
        if route.get("geometry") != [list(s.nodes[n]) for n in nodes]:
            error("C8_route_geometry", x)
        if not isclose(route.get("minutes", -1), minutes, abs_tol=1e-6) or not isclose(
            route.get("distance_km", -1), km, abs_tol=1e-6
        ):
            error("C8_route_measurement", x)
        return minutes, km

    for x, v in assignment.items():
        if x not in problem.slots or v.resource not in problem.resources:
            error("unknown_assignment", x)
            continue
        slot = problem.slots[x]
        i = slot.incident
        q = slot.requirement
        r = problem.resources[v.resource]
        used[r.id] += 1
        if r.role != q.role:
            error("C1_type", x)
        if not r.available or r.release_at > i.requested_at:
            error("C2_availability", x)
        if r.capacity < max(q.capacity, q.patients) or not set(q.capabilities) <= set(
            r.capabilities
        ):
            error("C6_capacity_capability", x)
        response, km = route_check(v.response, r.node, i.node, x)
        if response > i.deadline + 1e-7:
            error("C4_deadline", x)
        if v.patients != q.patients:
            error("C10_patient_count", x)
        if q.patients:
            h = problem.hospitals.get(v.hospital)
            if h is None or q.hospital_capability not in h.capabilities:
                error("C10_hospital", x)
            else:
                beds[h.id] += q.patients
                _, transport_km = route_check(v.transport, i.node, h.node, x)
                km += transport_km
        elif v.hospital is not None or v.transport is not None:
            error("C10_unexpected_transport", x)
        actual = r.dispatch_cost + r.cost_per_km * km
        cost += actual
        if not isclose(actual, v.cost, abs_tol=1e-6):
            error("C7_cost_measurement", x)
    for rid, count in used.items():
        if count > 1:
            error("C3_exclusivity", rid)
    for hid, count in beds.items():
        if count > problem.hospitals[hid].beds:
            error("C10_hospital_beds", hid)
    if cost > s.budget + 1e-6:
        error("C7_budget", "global")
    if require_complete and len(assignment) != len(problem.slots):
        error("C9_missing_requirements", "global")
    return {
        "valid": not errors,
        "complete": len(assignment) == len(problem.slots),
        "violations": errors,
        "violation_count": len(errors),
        "deadline_violations": sum(e["constraint"] == "C4_deadline" for e in errors),
        "budget_violations": sum(e["constraint"].startswith("C7") for e in errors),
        "total_cost": round(cost, 2),
    }
