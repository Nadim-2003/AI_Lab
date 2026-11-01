"""Look ahead over all unassigned variables, including shared global constraints."""


def forward_check(engine, domains):
    trail = []
    for y in domains:
        if y in engine.assignment:
            continue
        kept = [v for v in domains[y] if not engine.check(y, v)[1]]
        if len(kept) != len(domains[y]):
            trail.append((y, domains[y]))
            engine.metrics["pruned_values"] += len(domains[y]) - len(kept)
            domains[y] = kept
        if not kept:
            engine.metrics["domain_wipeouts"] += 1
            engine.event("forward_wipeout", variable=y)
            return False, trail
    return True, trail


def restore(domains, trail):
    for x, old in reversed(trail):
        domains[x] = old
