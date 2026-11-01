"""Run actual measurements; no fabricated tables. Execute from AI_Lab_02."""

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.models import Generate, Options, Experiment
from backend.app.evaluation import experiment


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=float, default=0.35)
    parser.add_argument("--steps", type=int, default=3000)
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--kind", choices=["all", "scale", "deadline", "pressure"], default="all"
    )
    parser.add_argument("--output", type=Path, default=Path("results"))
    args = parser.parse_args()
    methods = [
        Options(mrv=False, degree=False, severity_order=False),
        Options(degree=False),
        Options(lcv=True),
        Options(algorithm="backjumping"),
        Options(algorithm="forward_checking"),
        Options(algorithm="arc_consistency"),
        Options(algorithm="local_search"),
    ]
    for o in methods:
        o.timeout = args.timeout
        o.max_steps = args.steps
    args.output.mkdir(parents=True, exist_ok=True)
    for kind in (
        ["scale", "deadline", "pressure"] if args.kind == "all" else [args.kind]
    ):
        request = Experiment(
            kind=kind,
            generation=Generate(count=20, seed=args.seed),
            options=methods,
            repeats=args.repeats,
        )
        print(
            f"Running {kind}: {args.repeats} repeats, {args.timeout}s / {args.steps} steps per method",
            flush=True,
        )
        result = experiment(request)
        result["limits"] = {"timeout_seconds": args.timeout, "steps": args.steps}
        result["measurement_note"] = (
            "Actual current-instance measurements. Runtime excludes scenario/routing/domain preparation, serialization, final validation and UI."
        )
        (args.output / f"{kind}.json").write_text(json.dumps(result, indent=2))
        with (args.output / f"{kind}.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(
                stream,
                lineterminator="\n",
                fieldnames=[
                    "variant",
                    "incidents",
                    "method",
                    "mrv",
                    "lcv",
                    "repeat",
                    "status",
                    "full",
                    "partial",
                    "unserved",
                    "units",
                    "steps",
                    "checks",
                    "backtracks",
                    "backjumps",
                    "runtime_ms",
                    "violations",
                ],
            )
            writer.writeheader()
            for row in result["rows"]:
                writer.writerow(
                    dict(
                        variant=row["variant"],
                        incidents=row["incident_count"],
                        method=row["options"]["algorithm"],
                        mrv=row["options"]["mrv"],
                        lcv=row["options"]["lcv"],
                        repeat=row["repeat"],
                        status=row["status"],
                        full=row["summary"]["fully_served"],
                        partial=row["summary"]["partially_served"],
                        unserved=row["summary"]["unserved"],
                        units=row["summary"]["allocated_units"],
                        steps=row["metrics"]["search_steps"],
                        checks=row["metrics"]["constraint_checks"],
                        backtracks=row["metrics"]["backtracks"],
                        backjumps=row["metrics"]["backjumps"],
                        runtime_ms=round(row["metrics"]["runtime_ms"], 3),
                        violations=row["validation"]["violation_count"],
                    )
                )
        print(
            f"Saved {kind}: {len(result['rows'])} measured runs, {sum(r['validation']['violation_count'] for r in result['rows'])} returned hard violations",
            flush=True,
        )


if __name__ == "__main__":
    main()
