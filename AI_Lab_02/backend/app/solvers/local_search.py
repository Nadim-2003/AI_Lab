import random


def violations(engine, assignment):
    engine.p.prepare(assignment)
    bad = {}
    for x, v in assignment.items():
        _, codes = engine.check(x, v, assignment)
        if codes:
            bad[x] = codes
    return bad


def feasible_subset(engine, assignment):
    kept = {}
    order = sorted(
        assignment,
        key=lambda x: (
            -engine.p.slots[x].incident.severity,
            engine.p.slots[x].incident.deadline,
            x,
        ),
    )
    for x in order:
        engine.p.prepare(kept)
        if not engine.check(x, assignment[x], kept)[1]:
            kept[x] = assignment[x]
    engine.p.prepare(engine.assignment)
    if len(kept) > len(engine.best):
        engine.best = dict(kept)


def search(engine, domains):
    rng = random.Random(engine.o.seed)
    if any(not d for d in domains.values()):
        # Empty unary domains prove a complete solution impossible.
        candidate = {x: rng.choice(d) for x, d in domains.items() if d}
        feasible_subset(engine, candidate)
        return False, {"empty_domains": sum(not d for d in domains.values())}
    last = {}
    per_restart = max(1, engine.o.max_steps // (engine.o.restarts + 1))
    for restart in range(engine.o.restarts + 1):
        engine.metrics["restarts"] = restart
        engine.assignment = {x: rng.choice(d) for x, d in domains.items()}
        for _ in range(per_restart):
            engine.step()
            bad = violations(engine, engine.assignment)
            last = {x: sorted(codes) for x, codes in bad.items()}
            if not bad:
                engine.best = dict(engine.assignment)
                return True, {}
            feasible_subset(engine, engine.assignment)
            x = rng.choice(sorted(bad))
            # Min-conflicts with random tie breaks; all candidates are unary-feasible.
            best_score = None
            choices = []
            for value in domains[x]:
                engine.metrics["assignments_attempted"] += 1
                engine.p.prepare(engine.assignment)
                _, codes = engine.check(x, value)
                # Count competing resources and cumulative violations for X.
                causes, _ = engine.p.conflicts(x, value, engine.assignment)
                score = len(causes) + len(codes)
                if best_score is None or score < best_score:
                    best_score = score
                    choices = [value]
                elif score == best_score:
                    choices.append(value)
            engine.assignment[x] = rng.choice(choices)
            engine.context()
    return False, last
