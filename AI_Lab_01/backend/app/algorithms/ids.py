from .core import Search


def run(graph, start, goal, cost, limits, heuristic=None):
    search = Search(graph, start, goal, cost, limits)
    for bound in range(limits.max_depth + 1):
        stack, best_depth, cutoff = [(start, [])], {start: 0}, False
        while stack and search.allowed():
            node, path = stack.pop()
            if node == goal:
                return search.result('IDS', path)
            if len(path) >= bound:
                cutoff = True
                continue
            for target, edge, value in reversed(list(search.expand(node))):
                depth = len(path) + 1
                if depth < best_depth.get(target, float('inf')):
                    best_depth[target] = depth
                    stack.append((target, path + [edge]))
                    search.generated += 1
        if not search.allowed():
            return search.result('IDS')
        if not cutoff:
            return search.result('IDS')
    search.reason = 'depth_limit'
    return search.result('IDS')
