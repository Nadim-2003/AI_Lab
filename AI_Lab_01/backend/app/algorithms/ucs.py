from heapq import heappop, heappush
from itertools import count
from .core import Search, reconstruct


def run(graph, start, goal, cost, limits, heuristic=None):
    search = Search(graph, start, goal, cost, limits)
    order, distances, parents = count(), {start: 0}, {}
    queue = [(0, next(order), start)]
    while queue and search.allowed():
        distance, _, node = heappop(queue)
        if distance != distances[node]:
            continue
        if node == goal:
            return search.result('UCS', reconstruct(parents, start, goal))
        for target, edge, value in search.expand(node):
            candidate = distance + value
            if candidate < distances.get(target, float('inf')):
                distances[target], parents[target] = candidate, edge
                heappush(queue, (candidate, next(order), target))
                search.generated += 1
    return search.result('UCS')
