"""Directed, accessible shortest-time routes. Supporting algorithm, not CSP search."""

import heapq
import math
import networkx as nx


def distance(a, b):
    lon1, lat1, lon2, lat2 = map(math.radians, (*a, *b))
    x = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 6371 * 2 * math.asin(min(1, math.sqrt(x)))


class Router:
    def __init__(self, scenario):
        self.scenario = scenario
        self.roads = {e.id: e for e in scenario.roads}
        # Preserve Lab 1's directed MultiDiGraph / explicit parallel-edge identity.
        self.graph = nx.MultiDiGraph()
        self.graph.add_nodes_from(
            (n, {"x": lon, "y": lat}) for n, (lon, lat) in scenario.nodes.items()
        )
        for e in scenario.roads:
            self.graph.add_edge(e.u, e.v, key=e.id, road=e)
        self.adj = {
            n: [
                data["road"]
                for _, _, data in self.graph.out_edges(n, data=True)
                if not data["road"].blocked
            ]
            for n in self.graph
        }
        self.cache = {}
        self.routes = {}

    def route(self, start, target):
        if (start, target) in self.routes:
            return self.routes[start, target]
        if start not in self.cache:
            costs, parents, queue = {start: 0.0}, {}, [(0.0, start)]
            while queue:
                cost, u = heapq.heappop(queue)
                if cost != costs[u]:
                    continue
                for edge in self.adj[u]:
                    new = cost + edge.distance_km / edge.speed_kph * 60 * edge.traffic
                    if new < costs.get(edge.v, math.inf):
                        costs[edge.v], parents[edge.v] = new, edge.id
                        heapq.heappush(queue, (new, edge.v))
            self.cache[start] = costs, parents
        costs, parents = self.cache[start]
        if target not in costs:
            return None
        edges, u = [], target
        while u != start:
            edge = self.roads[parents[u]]
            edges.append(edge.id)
            u = edge.u
        edges.reverse()
        nodes = [start] + [self.roads[e].v for e in edges]
        result = {
            "origin": start,
            "destination": target,
            "edges": edges,
            "nodes": nodes,
            "geometry": [list(self.scenario.nodes[n]) for n in nodes],
            "minutes": costs[target],
            "distance_km": sum(self.roads[e].distance_km for e in edges),
        }
        self.routes[start, target] = result
        return result
