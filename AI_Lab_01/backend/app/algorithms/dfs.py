from .core import Search


def run(graph, start, goal, cost, limits, heuristic=None):
    search = Search(graph, start, goal, cost, limits)
    stack, best_depth = [(start, [])], {start: 0}
    cutoff = False
    while stack and search.allowed():
        node, path = stack.pop()
        if node == goal:
            return search.result('DFS', path)
        if len(path) >= limits.max_depth:
            cutoff = True
            continue
        for target, edge, value in reversed(list(search.expand(node))):
            depth = len(path) + 1
            if depth < best_depth.get(target, float('inf')):
                best_depth[target] = depth
                stack.append((target, path + [edge]))
                search.generated += 1
    if cutoff and search.reason == 'unreachable':
        search.reason = 'depth_limit'
    return search.result('DFS')
