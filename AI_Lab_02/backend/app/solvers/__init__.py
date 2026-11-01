from .common import Engine, SearchLimit
from .backtracking import search as backtrack
from .backjumping import search as backjump
from .arc_consistency import ac3
from .local_search import search as local


def run(problem, options):
    engine = Engine(problem, options)
    domains = {x: list(d) for x, d in problem.domains.items()}
    status = "infeasible"
    unresolved = {}
    try:
        if options.algorithm == "local_search":
            solved, unresolved = local(engine, domains)
            status = (
                "feasible"
                if solved
                else (
                    "infeasible"
                    if any(not d for d in domains.values())
                    else "local_limit"
                )
            )
        elif options.algorithm == "backjumping":
            solved, _ = backjump(engine, domains)
            status = "feasible" if solved else "infeasible"
        else:
            valid = (
                ac3(engine, domains) if options.algorithm == "arc_consistency" else True
            )
            solved = valid and backtrack(
                engine,
                domains,
                forward=options.algorithm == "forward_checking",
                mac=options.algorithm == "arc_consistency" and options.mac,
            )
            status = "feasible" if solved else "infeasible"
    except SearchLimit as exc:
        status = str(exc)
        if options.algorithm == "local_search":
            # A stopped complete local-search assignment may still contain conflicts.
            unresolved = {"bounded_before_convergence": True}
    if options.algorithm == "local_search":
        from collections import Counter

        problem.prepare(engine.assignment)
        counts = Counter()
        for x, v in engine.assignment.items():
            _, codes = problem.conflicts(x, v, engine.assignment)
            counts.update(codes)
        unresolved = {
            "raw_assignment_conflicts": dict(counts),
            "raw_conflicting_slot_constraints": sum(counts.values()),
            "raw_missing_slots": len(problem.slots) - len(engine.assignment),
            "termination": status,
        }
    from time import perf_counter

    engine.metrics["runtime_ms"] = (perf_counter() - engine.started) * 1000
    if options.algorithm == "local_search":
        for key in [
            "backtracks",
            "backjumps",
            "skipped_levels",
            "arc_revisions",
            "domain_wipeouts",
            "pruned_values",
            "conflict_sets",
            "max_conflict_set",
        ]:
            engine.metrics[key] = None
    elif options.algorithm != "backjumping":
        for key in ["backjumps", "skipped_levels", "conflict_sets", "max_conflict_set"]:
            engine.metrics[key] = None
    if options.algorithm != "local_search":
        engine.metrics["restarts"] = None
    if options.algorithm != "arc_consistency":
        engine.metrics["arc_revisions"] = None
    if options.algorithm not in {"forward_checking", "arc_consistency"}:
        engine.metrics["pruned_values"] = None
        engine.metrics["domain_wipeouts"] = None
    return (
        engine.best,
        status,
        engine.metrics,
        dict(engine.failures),
        engine.trace,
        unresolved,
    )
