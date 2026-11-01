from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.models import Generate, Options, Experiment
from backend.app.generation import generate
from backend.app.evaluation import experiment
from backend.app.service import solve


def test_reproducible_and_scaling():
    a = generate(Generate(count=10, seed=7))
    b = generate(Generate(count=10, seed=7))
    assert a == b
    large = generate(Generate(count=300, seed=7))
    assert len(large.incidents) == 300
    assert len(large.resources) > len(a.resources) * 10
    assert len({r.station for r in large.resources}) == 5
    assert any(
        sum(r.station == s.id and r.role == "ambulance" for r in large.resources) > 1
        for s in large.stations
    )


def test_deadline_experiments_hold_configuration():
    request = Experiment(
        kind="deadline",
        generation=Generate(count=3),
        options=[Options(timeout=1, max_steps=100)],
    )
    result = experiment(request)
    assert len(result["rows"]) == 3
    # No RNG is consumed when changing deadlines.
    a = generate(request.generation)
    b = a.model_copy(deep=True)
    for i in b.incidents:
        i.deadline = 30
    assert a.resources == b.resources and a.roads == b.roads
    assert [i.node for i in a.incidents] == [i.node for i in b.incidents]
    assert all(row["validation"]["valid"] for row in result["rows"])


def test_api_validation_and_solve(small):
    client = TestClient(app)
    assert client.get("/api/health").json()["lab"] == 2
    assert client.post("/api/scenarios", json={"count": 301}).status_code == 422
    response = client.post(
        "/api/solve",
        json={
            "scenario": small.model_dump(),
            "options": {"algorithm": "forward_checking"},
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "feasible"
    bad = small.model_dump()
    bad["resources"][0]["node"] = "missing"
    assert client.post("/api/solve", json={"scenario": bad}).status_code == 422
    a = client.post("/api/scenarios", json={"demo": "medical"}).json()
    assert a["source"].startswith("Simulated")


def test_comparison_identical_scenario(small):
    response = TestClient(app).post(
        "/api/compare",
        json={
            "scenario": small.model_dump(),
            "options": [{"algorithm": "backtracking"}, {"algorithm": "backjumping"}],
        },
    )
    assert response.status_code == 200
    assert len(response.json()["results"]) == 2
    assert all(r["summary"]["fully_served"] == 2 for r in response.json()["results"])


def test_custom_demand_rule():
    s = generate(
        Generate(
            count=2,
            rules={
                "earthquake": [
                    {
                        "role": "rescue",
                        "quantity": 2,
                        "capacity": 4,
                        "capabilities": ["rescue"],
                    }
                ]
            },
        )
    )
    assert all(i.category == "earthquake" for i in s.incidents)
    assert all(i.requirements[0].quantity == 2 for i in s.incidents)


def test_demos():
    for demo in ["medical", "fire", "blocked"]:
        s = generate(Generate(demo=demo, block_fraction=0))
        r = solve(s, Options())
        assert r["status"] == "feasible"
        if demo == "fire":
            assert {"fire", "ambulance"} <= set(a["role"] for a in r["assignments"])
        if demo == "blocked":
            assert all(
                "6:3>6:4" not in a["response"]["edges"] for a in r["assignments"]
            )


def test_backjumping_production_witness():
    from backend.app.evaluation import compare

    s = generate(Generate(demo="backjumping"))
    options = [
        Options(algorithm=a, mrv=False, degree=False, lcv=False, severity_order=False)
        for a in ["backtracking", "backjumping", "forward_checking"]
    ]
    bt, cbj, fc = compare(s, options)["results"]
    assert all(
        r["status"] == "feasible" and r["validation"]["valid"] for r in [bt, cbj, fc]
    )
    assert cbj["metrics"]["backjumps"] == 1
    assert cbj["metrics"]["skipped_levels"] == 1
    assert (
        fc["metrics"]["assignments_attempted"]
        < cbj["metrics"]["assignments_attempted"]
        < bt["metrics"]["assignments_attempted"]
    )
