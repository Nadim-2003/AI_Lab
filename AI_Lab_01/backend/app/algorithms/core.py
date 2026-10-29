from dataclasses import dataclass
from math import isfinite
from time import perf_counter


@dataclass(frozen=True)
class Limits:
    max_expansions: int = 100000
    max_depth: int = 100
    timeout_seconds: float = 5.0
    trace_limit: int = 0


class Search:
    def __init__(self, graph, start, goal, cost, limits):
        if start not in graph or goal not in graph:
            raise ValueError('Start and destination must exist in the graph')
        self.graph, self.start, self.goal = graph, start, goal
        self.cost, self.limits = cost, limits
        self.began = perf_counter()
        self.expanded = 0
        self.generated = 1
        self.trace = []
        self.reason = 'unreachable'

    def allowed(self):
        if self.expanded >= self.limits.max_expansions:
            self.reason = 'expansion_limit'
            return False
        if perf_counter() - self.began >= self.limits.timeout_seconds:
            self.reason = 'timeout'
            return False
        return True

    def expand(self, node):
        self.expanded += 1
        if len(self.trace) < self.limits.trace_limit:
            self.trace.append(str(node))
        for target, keyed in self.graph.adj[node].items():
            for key, attrs in keyed.items():
                value = self.cost(node, target, key, attrs)
                if value is None:
                    continue
                if not isfinite(value) or value < 0:
                    raise ValueError('Traversable costs must be finite and nonnegative')
                yield target, (node, target, key), value

    def result(self, name, edges=None):
        found = edges is not None
        edges = edges or []
        return {
            'algorithm': name, 'found': found,
            'status': 'found' if found else self.reason,
            'nodes': [str(self.start)] + [str(e[1]) for e in edges] if found else [],
            'edges': [[str(u), str(v), str(k)] for u, v, k in edges],
            'cost': sum(self.cost(u, v, k, self.graph[u][v][k]) for u, v, k in edges) if found else None,
            'distance_km': sum(float(self.graph[u][v][k]['length']) for u, v, k in edges) / 1000 if found else None,
            'expanded': self.expanded, 'generated': self.generated,
            'execution_ms': (perf_counter() - self.began) * 1000,
            'trace': self.trace, 'trace_truncated': self.expanded > len(self.trace),
        }


def reconstruct(parents, start, goal):
    route = []
    current = goal
    while current != start:
        edge = parents[current]
        route.append(edge)
        current = edge[0]
    return list(reversed(route))
