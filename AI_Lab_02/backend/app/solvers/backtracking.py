from .arc_consistency import ac3
from .forward_checking import forward_check, restore


def search(engine, domains, forward=False, mac=False):
    engine.bound()
    if len(engine.assignment) == len(engine.p.slots):
        return True
    x = engine.select(domains)
    for value in engine.ordered_values(x, domains):
        engine.step()
        engine.metrics["assignments_attempted"] += 1
        if engine.check(x, value)[1]:
            continue
        engine.put(x, value)
        engine.event("assign", variable=x, resource=value.resource)
        trail = []
        valid = True
        if forward:
            valid, trail = forward_check(engine, domains)
        if valid and mac:
            # Copy-on-branch for AC propagation; the parent's domains stay intact.
            child = {
                y: ([engine.assignment[y]] if y in engine.assignment else list(d))
                for y, d in domains.items()
            }
            valid = ac3(engine, child)
        else:
            child = domains
        if valid and search(engine, child, forward, mac):
            return True
        restore(domains, trail)
        engine.remove(x)
        engine.metrics["backtracks"] += 1
    return False
