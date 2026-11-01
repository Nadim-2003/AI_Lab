"""AC-3 on binary exclusivity/pairwise bed constraints, never global budget."""

from collections import deque


def ac3(engine, domains, arcs=None):
    p = engine.p
    queue = deque(
        arcs if arcs is not None else ((x, y) for x in domains for y in p.neighbors[x])
    )
    pending = set(queue)
    while queue:
        engine.bound()
        x, y = queue.popleft()
        pending.discard((x, y))
        kept = []
        for a in domains[x]:
            supported = False
            for b in domains[y]:
                engine.metrics["constraint_checks"] += 1
                if engine.metrics["constraint_checks"] % 128 == 0:
                    engine.bound()
                if p.compatible(x, a, y, b):
                    supported = True
                    break
            if supported:
                kept.append(a)
        if len(kept) != len(domains[x]):
            engine.metrics["arc_revisions"] += 1
            engine.metrics["pruned_values"] += len(domains[x]) - len(kept)
            domains[x] = kept
            if not kept:
                engine.metrics["domain_wipeouts"] += 1
                engine.event("arc_wipeout", variable=x, neighbor=y)
                return False
            for z in p.neighbors[x] - {y}:
                if (z, x) not in pending:
                    queue.append((z, x))
                    pending.add((z, x))
    return True
