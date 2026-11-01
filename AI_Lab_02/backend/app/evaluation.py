"""Measured comparisons; clone one immutable base for deadline/pressure trials."""

import hashlib
import json
from time import perf_counter
from .generation import generate
from .problem import Problem
from .service import solve


def fingerprint(scenario):
    return hashlib.sha256(
        json.dumps(scenario.model_dump(), sort_keys=True).encode()
    ).hexdigest()[:16]


def compare(scenario, options):
    began = perf_counter()
    p = Problem(scenario)
    preparation_ms = (perf_counter() - began) * 1000
    digest = fingerprint(scenario)
    return {
        "scenario_hash": digest,
        "preparation_ms": preparation_ms,
        "results": [solve(scenario, o, p) for o in options],
    }


def experiment(request):
    began = perf_counter()
    base = generate(request.generation)
    variants = []
    if request.kind == "deadline":
        for minutes in [30, 60, 120]:
            s = base.model_copy(deep=True)
            for i in s.incidents:
                i.deadline = minutes
            variants.append((str(minutes), s))
    elif request.kind == "scale":
        variants = [
            (
                str(n),
                generate(
                    request.generation.model_copy(update={"count": n, "demo": "custom"})
                ),
            )
            for n in request.sizes
        ]
    else:
        variants = [("baseline", base)]
        for name in [
            "budget_low",
            "budget_high",
            "ambulance_shortage",
            "rescue_shortage",
            "fire_busy",
            "no_hospital",
            "blocked_corridor",
            "high_severity",
        ]:
            s = base.model_copy(deep=True)
            if name == "budget_low":
                s.budget *= 0.35
            if name == "budget_high":
                s.budget *= 2
            if name in ["ambulance_shortage", "rescue_shortage"]:
                role = "ambulance" if name == "ambulance_shortage" else "rescue"
                pool = [r for r in s.resources if r.role == role]
                for r in pool[: max(1, len(pool) // 2)]:
                    r.available = False
            if name == "fire_busy":
                for r in s.resources:
                    if r.role == "fire":
                        r.available = False
                        r.release_at = 120
            if name == "no_hospital":
                for h in s.hospitals:
                    h.beds = 0
            if name == "blocked_corridor":
                for edge in s.roads:
                    if (int(edge.u.split(":")[1]) <= 3) != (
                        int(edge.v.split(":")[1]) <= 3
                    ):
                        edge.blocked = True
            if name == "high_severity":
                for i in s.incidents:
                    i.severity = 5
            variants.append((name, s))
    generation_ms = (perf_counter() - began) * 1000
    rows = []
    for label, s in variants:
        began = perf_counter()
        p = Problem(s)
        preparation_ms = (perf_counter() - began) * 1000
        for repeat in range(request.repeats):
            for options in request.options:
                # Vary solver seed only: the physical scenario remains identical.
                o = options.model_copy(update={"seed": options.seed + repeat})
                result = solve(s, o, p)
                rows.append(
                    {
                        "variant": label,
                        "shared_preparation_ms": preparation_ms,
                        "incident_count": len(s.incidents),
                        "repeat": repeat,
                        "scenario_hash": fingerprint(s),
                        "options": o.model_dump(),
                        "status": result["status"],
                        "summary": result["summary"],
                        "metrics": result["metrics"],
                        "validation": result["validation"],
                        "domain_rejections": result["domain_rejections"],
                        "constraint_failures": result["constraint_failures"],
                        "empty_domains": len(result["empty_domains"]),
                    }
                )
    return {
        "kind": request.kind,
        "generation_ms": generation_ms,
        "generation": request.generation.model_dump(),
        "rows": rows,
        "notes": "Runtime measures solver only, excluding routing/domain preparation, final validation and rendering. Partial results are valid subsets, not maximum allocations. Same scenario hash identifies identical input.",
    }
