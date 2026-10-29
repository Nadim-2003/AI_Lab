from heapq import heappop, heappush
from itertools import count
from .core import Search, reconstruct


def run(graph, start, goal, cost, limits, heuristic=None):
    search = Search(graph, start, goal, cost, limits)
    heuristic = heuristic or (lambda node: 0)
    order, distances, parents = count(), {start: 0}, {}
    queue = [(heuristic(start), next(order), 0, start)]
    while queue and search.allowed():
        _, _, distance, node = heappop(queue)
        if distance != distances[node]:
            continue
        if node == goal:
            return search.result('A*', reconstruct(parents, start, goal))
        for target, edge, value in search.expand(node):
            candidate = distance + value
            if candidate < distances.get(target, float('inf')):
                distances[target], parents[target] = candidate, edge
                heappush(queue, (candidate + heuristic(target), next(order), candidate, target))
                search.generated += 1
    return search.result('A*')
