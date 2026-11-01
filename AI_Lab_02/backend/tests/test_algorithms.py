import itertools
from dataclasses import dataclass
from types import SimpleNamespace
import pytest
from backend.app.models import Options
from backend.app.problem import Value, Problem
from backend.app.solvers import run
from backend.app.solvers.common import Engine
from backend.app.solvers.arc_consistency import ac3
from backend.app.solvers.forward_checking import forward_check, restore


class Binary:
    def __init__(self, domains):
        self.domains = {
            x: [Value(r, None, {}, None, 0, 0) for r in rs] for x, rs in domains.items()
        }
        self.slots = {
            x: SimpleNamespace(incident=SimpleNamespace(severity=1, deadline=60))
            for x in domains
        }
        self.neighbors = {
            x: {y for y in domains if x != y and set(domains[x]) & set(domains[y])}
            for x in domains
        }

    def compatible(self, x, a, y, b):
        return a.resource != b.resource

    def conflicts(self, x, v, assignment):
        causes = {
            y for y, w in assignment.items() if y != x and v.resource == w.resource
        }
        return causes, {"C3"} if causes else set()


def plain(**kwargs):
    return Options(mrv=False, degree=False, severity_order=False, **kwargs)


def test_cbj_really_skips_unrelated_variable():
    p = Binary({"A": ["r1", "r2"], "B": ["r3", "r4"], "C": ["r1"]})
    bt = run(p, plain())
    cbj = run(p, plain(algorithm="backjumping"))
    assert bt[1] == cbj[1] == "feasible"
    assert cbj[2]["skipped_levels"] >= 1
    assert cbj[2]["backjumps"] >= 1
    assert cbj[2]["assignments_attempted"] < bt[2]["assignments_attempted"]
    assert any(t["event"] == "skip_unrelated" and t["variable"] == "B" for t in cbj[4])


def test_forward_checking_restores_domains():
    p = Binary({"A": ["r1", "r2"], "B": ["r1"]})
    e = Engine(p, plain())
    domains = {x: list(d) for x, d in p.domains.items()}
    e.put("A", domains["A"][0])
    valid, trail = forward_check(e, domains)
    assert not valid and domains["B"] == []
    restore(domains, trail)
    e.remove("A")
    assert domains == p.domains
    fc = run(p, plain(algorithm="forward_checking"))
    assert fc[1] == "feasible"
    assert fc[0]["A"].resource == "r2"
    assert fc[2]["domain_wipeouts"] > 0


def test_ac3_filters_without_losing_solution():
    p = Binary({"A": ["r1", "r2"], "B": ["r1"]})
    domains = {x: list(d) for x, d in p.domains.items()}
    assert ac3(Engine(p, plain()), domains)
    assert [v.resource for v in domains["A"]] == ["r2"]
    p = Binary({"A": ["r1"], "B": ["r1"]})
    assert not ac3(Engine(p, plain()), {x: list(d) for x, d in p.domains.items()})


@pytest.mark.parametrize(
    "algorithm", ["backtracking", "backjumping", "forward_checking", "arc_consistency"]
)
def test_against_exhaustive_reference(algorithm):
    # Exhaust all nonempty domain subsets over three resources for three slots.
    subsets = [
        list(c)
        for n in [1, 2, 3]
        for c in itertools.combinations(["r1", "r2", "r3"], n)
    ]
    for ds in itertools.product(subsets, repeat=3):
        p = Binary(dict(zip(["A", "B", "C"], ds)))
        expected = any(len(set(values)) == 3 for values in itertools.product(*ds))
        result = run(p, plain(algorithm=algorithm, timeout=1))
        assert (result[1] == "feasible") == expected, ds
        assert len({v.resource for v in result[0].values()}) == len(result[0])


def test_global_budget_cbj_matches_exhaustive(small):
    small.budget = 1000
    p = Problem(small)
    expected = any(
        a.resource != b.resource and a.cost + b.cost <= small.budget
        for a, b in itertools.product(*p.domains.values())
    )
    for algorithm in [
        "backtracking",
        "backjumping",
        "forward_checking",
        "arc_consistency",
    ]:
        assert (run(p, plain(algorithm=algorithm))[1] == "feasible") == expected


def test_mrv_degree_lcv_and_mac():
    p = Binary({"A": ["r1", "r2"], "B": ["r1"], "C": ["r1", "r3"]})
    e = Engine(p, Options(mrv=True, degree=True, lcv=True))
    assert e.select(p.domains) == "B"
    assert (
        e.ordered_values("A", p.domains)[0].resource == "r2"
    )  # r2 leaves both neighbors unchanged
    result = run(p, Options(algorithm="arc_consistency", mac=True))
    assert result[1] == "feasible"


def test_forward_lookahead_avoids_unrelated_subtree():
    p = Binary({"A": ["r1", "r2"], "B": ["r3", "r4"], "C": ["r1"]})
    bt = run(p, plain())
    fc = run(p, plain(algorithm="forward_checking"))
    assert bt[1] == fc[1] == "feasible"
    assert fc[2]["assignments_attempted"] < bt[2]["assignments_attempted"]
    assert fc[2]["pruned_values"] > 0


def test_global_beds_not_incorrectly_replaced_by_binary_ac(small):
    from backend.app.models import Resource

    third = small.incidents[1].model_copy(deep=True)
    third.id = "C"
    small.incidents.append(third)
    r = small.resources[1].model_copy(deep=True)
    r.id = "R3"
    small.resources.append(r)
    small.hospitals[0].beds = 2
    p = Problem(small)
    domains = {x: list(d) for x, d in p.domains.items()}
    # Every pair of patients fits; three patients do not. AC must not invent a proof.
    assert ac3(Engine(p, plain()), domains)
    for algo in ["backtracking", "backjumping", "forward_checking", "arc_consistency"]:
        result = run(p, plain(algorithm=algo))
        assert result[1] == "infeasible"
        assert len(result[0]) <= 2


def test_global_constraints_against_independent_exhaustive(small):
    import random
    from backend.app.validation import validate

    rng = random.Random(12)
    third = small.incidents[1].model_copy(deep=True)
    third.id = "C"
    small.incidents.append(third)
    r = small.resources[1].model_copy(deep=True)
    r.id = "R3"
    small.resources.append(r)
    h = small.hospitals[0].model_copy(deep=True)
    h.id = "H2"
    h.node = "a"
    small.hospitals.append(h)
    for _ in range(15):
        small.budget = rng.choice([1000, 1600, 2400, 10000])
        for hospital in small.hospitals:
            hospital.beds = rng.randint(0, 3)
        p = Problem(small)
        expected = any(
            validate(p, dict(zip(p.slots, values)), True)["valid"]
            for values in itertools.product(*p.domains.values())
        )
        for algorithm in [
            "backtracking",
            "backjumping",
            "forward_checking",
            "arc_consistency",
        ]:
            actual = run(
                p, Options(algorithm=algorithm, mrv=True, lcv=True, mac=True, timeout=2)
            )
            assert (actual[1] == "feasible") == expected
            assert validate(p, actual[0])["valid"]


def test_non_applicable_metrics_are_null():
    p = Binary({"A": ["r1"], "B": ["r2"]})
    result = run(p, plain())
    assert all(
        result[2][key] is None
        for key in [
            "backjumps",
            "skipped_levels",
            "restarts",
            "pruned_values",
            "arc_revisions",
            "domain_wipeouts",
        ]
    )
    result = run(p, plain(algorithm="arc_consistency"))
    assert result[2]["arc_revisions"] == 0
