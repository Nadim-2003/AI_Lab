"""Produce complete, editable scenarios and a measured CBJ witness."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.models import Generate, Options
from backend.app.generation import generate
from backend.app.evaluation import compare

root = Path(__file__).resolve().parents[1] / "demos"
root.mkdir(exist_ok=True)
for demo in [
    "medical",
    "fire",
    "competition",
    "blocked",
    "insufficient",
    "backjumping",
]:
    scenario = generate(Generate(demo=demo, block_fraction=0))
    (root / f"{demo}.json").write_text(scenario.model_dump_json(indent=2))
    if demo == "backjumping":
        options = [
            Options(
                algorithm=algorithm,
                mrv=False,
                degree=False,
                lcv=False,
                severity_order=False,
            )
            for algorithm in [
                "backtracking",
                "backjumping",
                "forward_checking",
                "arc_consistency",
                "local_search",
            ]
        ]
        (root / "backjumping-comparison.json").write_text(
            json.dumps(compare(scenario, options), indent=2)
        )
for n in [10, 20, 30, 50, 100, 150, 250, 300]:
    (root / f"scale-{n}.generation.json").write_text(
        Generate(count=n).model_dump_json(indent=2)
    )
