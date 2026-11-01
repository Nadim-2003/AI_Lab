from dataclasses import replace
import pytest
from backend.app.models import Options, Requirement
from backend.app.problem import Problem
from backend.app.service import solve
from backend.app.validation import validate
from backend.app.routing import Router


@pytest.mark.parametrize(
    "algorithm",
    [
        "backtracking",
        "backjumping",
        "forward_checking",
        "arc_consistency",
        "local_search",
    ],
)
def test_all_solvers_validate(small, algorithm):
    result = solve(small, Options(algorithm=algorithm, max_steps=5000, timeout=2))
    assert result["status"] == "feasible"
    assert result["validation"]["valid"]
    assert result["summary"]["fully_served"] == 2
    assert len({a["resource"] for a in result["assignments"]}) == 2
    assert all(a["transport_minutes"] >= 0 for a in result["assignments"])


@pytest.mark.parametrize(
    "change,code",
    [
        ("type", "C1_type"),
        ("availability", "C2_availability"),
        ("release", "C2_availability"),
        ("capacity", "C6_capacity_capability"),
        ("capability", "C6_capacity_capability"),
        ("deadline", "C4_deadline"),
        ("budget", "C7_budget"),
        ("hospital", "C10_hospital"),
    ],
)
def test_unary_restrictions(small, change, code):
    small.resources = small.resources[:1]
    r = small.resources[0]
    if change == "type":
        r.role = "fire"
    if change == "availability":
        r.available = False
    if change == "release":
        r.release_at = 1
    if change == "capacity":
        r.capacity = 1
        small.incidents[0].requirements[0].capacity = 3
    if change == "capability":
        r.capabilities = []
    if change == "deadline":
        small.incidents[0].deadline = 0.1
    if change == "budget":
        small.budget = 1
    if change == "hospital":
        small.hospitals[0].beds = 0
    p = Problem(small)
    assert p.domains["A/0/0"] == []
    assert p.rejections["A/0/0"][code] > 0


def test_blocked_alternate_and_unreachable(small):
    router = Router(small)
    assert router.route("a", "c")["edges"] == ["ab", "bc"]
    small.roads[0].blocked = True
    assert Router(small).route("a", "c")["edges"] == ["ac"]
    small.roads[2].blocked = True
    assert Router(small).route("a", "c") is None


def test_transport_unreachable(small):
    small.roads = [e for e in small.roads if e.id not in ["bc", "ac"]]
    p = Problem(small)
    assert not p.domains["A/0/0"]
    assert p.rejections["A/0/0"]["C10_hospital"]


def test_multiresource_and_partial(small):
    small.incidents = small.incidents[:1]
    small.incidents[0].requirements.append(Requirement(role="fire"))
    r = solve(small, Options(mrv=False, degree=False, severity_order=False))
    assert r["status"] == "infeasible"
    assert r["summary"]["partially_served"] == 1
    assert r["summary"]["fully_served"] == 0
    assert r["validation"]["valid"]


def test_cumulative_beds_and_budget(small):
    small.hospitals[0].beds = 1
    result = solve(small, Options(algorithm="arc_consistency"))
    assert result["status"] == "infeasible"
    assert result["validation"]["valid"]
    small.hospitals[0].beds = 4
    small.budget = 700  # each unit alone fits but their sum does not
    result = solve(small, Options())
    assert result["status"] == "infeasible"
    assert result["constraint_failures"]["C7_budget"] > 0


def test_independent_validator_catches_tampering(small):
    p = Problem(small)
    a = p.domains["A/0/0"][0]
    b = next(v for v in p.domains["B/0/0"] if v.resource == a.resource)
    result = validate(p, {"A/0/0": a, "B/0/0": b})
    assert any(e["constraint"] == "C3_exclusivity" for e in result["violations"])
    assert not validate(p, {"A/0/0": replace(a, cost=0)})["valid"]
    small.roads[0].blocked = True
    assert not validate(p, {"A/0/0": a})["valid"]


def test_local_limit_returns_safe_subset(small):
    small.resources = small.resources[:1]
    r = solve(small, Options(algorithm="local_search", max_steps=5))
    assert r["status"] in ["local_limit", "step_limit"]
    assert r["validation"]["valid"]
    assert r["summary"]["fully_served"] < 2
    assert r["local_unresolved"]
    assert r["metrics"]["backtracks"] is None


def test_requirement_quantity_and_passenger_beds(small):
    small.incidents = small.incidents[:1]
    q = small.incidents[0].requirements[0]
    q.quantity = 2
    q.patients = 2
    r = solve(small, Options())
    assert r["status"] == "feasible"
    assert r["summary"]["allocated_units"] == 2
    assert sum(a["patients"] for a in r["assignments"]) == 4
    small.hospitals[0].beds = 3
    assert solve(small, Options())["status"] == "infeasible"


def test_hospital_capability_and_severity_policy(small):
    small.hospitals[0].capabilities = ["burns"]
    assert all(not d for d in Problem(small).domains.values())
    small.hospitals[0].capabilities = ["emergency"]
    small.resources = small.resources[:1]
    small.incidents[1].severity = 5
    small.incidents[0].severity = 1
    r = solve(small, Options(mrv=False, degree=False, severity_order=True))
    assert r["assignments"][0]["incident"] == "B"


def test_time_limit_status_does_not_claim_infeasible(small):
    result = solve(small, Options(max_steps=1, mrv=False))
    assert result["status"] == "step_limit"
    assert result["validation"]["valid"]
    assert result["summary"]["unserved"] >= 1
