"""Conflict-directed backjumping with dynamic-order conflict propagation.

A failing child returns responsible ancestors. If current X is absent, its
remaining values cannot fix the conflict: skip X. Otherwise absorb child-{X}
and try the next value. Global budget/bed causes include every contributor.
"""


def search(engine, domains):
    engine.bound()
    if len(engine.assignment) == len(engine.p.slots):
        return True, set()
    x = engine.select(domains)
    conflict = set()
    for value in engine.ordered_values(x, domains):
        engine.step()
        engine.metrics["assignments_attempted"] += 1
        causes, codes = engine.check(x, value)
        if codes:
            conflict.update(causes)
            continue
        engine.put(x, value)
        engine.event("assign", variable=x, resource=value.resource)
        solved, child = search(engine, domains)
        if solved:
            return True, set()
        engine.remove(x)
        if x not in child:
            engine.metrics["skipped_levels"] += 1
            engine.event("skip_unrelated", variable=x, conflict=sorted(child))
            return False, child
        engine.metrics["backtracks"] += 1
        conflict.update(child - {x})
    engine.metrics["conflict_sets"] += 1
    engine.metrics["max_conflict_set"] = max(
        engine.metrics["max_conflict_set"], len(conflict)
    )
    if conflict:
        # Count only jumps that skip at least one unrelated decision.
        target = next(y for y in reversed(engine.assignment) if y in conflict)
        nonchronological = target != next(reversed(engine.assignment))
        engine.metrics["backjumps"] += int(nonchronological)
        engine.event(
            "backjump" if nonchronological else "conflict_return",
            variable=x,
            target=target,
            conflict=sorted(conflict),
        )
    return False, conflict
