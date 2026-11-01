from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .models import Generate, SolveRequest, CompareRequest, Experiment
from .generation import generate
from .service import solve
from .evaluation import compare, experiment

app = FastAPI(title="AI Lab 2 — Emergency CSP", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://127.0.0.1:5174"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "alive", "lab": 2, "data": "simulated"}


@app.post("/api/scenarios")
def scenarios(request: Generate):
    try:
        return generate(request)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/solve")
def allocation(request: SolveRequest):
    return solve(request.scenario, request.options)


@app.post("/api/compare")
def comparison(request: CompareRequest):
    return compare(request.scenario, request.options)


@app.post("/api/experiments")
def experiments(request: Experiment):
    return experiment(request)


from .models import Scenario


@app.post("/api/validate-scenario")
def validate_scenario(scenario: Scenario):
    return scenario
