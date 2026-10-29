from collections import deque
from .core import Search, reconstruct


def run(graph, start, goal, cost, limits, heuristic=None):
    search = Search(graph, start, goal, cost, limits)
    queue, seen, parents = deque([start]), {start}, {}
    while queue and search.allowed():
        node = queue.popleft()
        if node == goal:
            return search.result('BFS', reconstruct(parents, start, goal))
        for target, edge, value in search.expand(node):
            if target not in seen:
                seen.add(target)
                parents[target] = edge
                queue.append(target)
                search.generated += 1
    return search.result('BFS')
