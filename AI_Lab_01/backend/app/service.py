import hashlib
import json
from math import isfinite
from collections import Counter
from pathlib import Path
from types import MappingProxyType
import networkx as nx
from pyproj import Transformer
from shapely.geometry import Point as GeoPoint
from shapely.strtree import STRtree
from shapely.geometry import LineString
from .algorithms import ALGORITHMS, Limits
from .geo import edge_geometry, haversine, route_geometry, valid_coordinate
from .models import Scenario, Conditions
from .store import Store


BUILTINS = {
    'normal': Scenario(name='Normal Day', description='Simulated baseline; no live traffic feed.'),
    'traffic': Scenario(name='Heavy Traffic', road_classes=['primary', 'secondary', 'trunk'], conditions=Conditions(traffic=1)),
    'rain': Scenario(name='Heavy Rain and Waterlogging', road_classes=['residential', 'tertiary', 'unclassified'], conditions=Conditions(rain=1, condition=0.5)),
    'night': Scenario(name='Night Travel', road_classes=['residential', 'service', 'unclassified'], conditions=Conditions(safety=1)),
    'blockage': Scenario(name='Road Blockage', description='Only explicitly selected directed edges are closed; edit roads or duplicate this scenario.'),
    'emergency': Scenario(name='Combined Emergency', conditions=Conditions(traffic=1, rain=1, condition=0.5, safety=1)),
}


def edge_id(u, v, key):
    return f'{u}:{v}:{key}'


class Service:
    def __init__(self, data_dir, graph=None):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.store = Store(self.data_dir / 'state.sqlite3')
        self.graph = None
        self.error = None
        self.places = []
        self.metadata = {}
        try:
            if graph is None:
                import osmnx as ox
                path = self.data_dir / 'dhaka.graphml'
                if not path.exists():
                    self.error = 'Road dataset missing. Run python scripts/acquire_data.py, then restart the backend.'
                    return
                graph = ox.load_graphml(path)
            if not graph.is_directed() or not graph.is_multigraph() or not graph.number_of_nodes():
                raise ValueError('Expected a nonempty directed MultiDiGraph')
            renamed = nx.relabel_nodes(graph, {n: str(n) for n in graph}, copy=True)
            normalized = nx.MultiDiGraph()
            normalized.graph.update(renamed.graph)
            normalized.add_nodes_from(renamed.nodes(data=True))
            for u, v, key, attrs in renamed.edges(keys=True, data=True):
                if not isfinite(float(attrs.get('length', -1))) or float(attrs.get('length', -1)) < 0:
                    raise ValueError('Road lengths must be finite and nonnegative')
                normalized.add_edge(u, v, key=str(key), **attrs)
            for _, attrs in normalized.nodes(data=True):
                if not valid_coordinate([float(attrs['x']), float(attrs['y'])]):
                    raise ValueError('Invalid graph coordinate')
            self.graph = nx.freeze(normalized)
            self.edges = {edge_id(u, v, k): (u, v, k) for u, v, k in self.graph.edges(keys=True)}
            self.node_ids = list(self.graph)
            self.transform = Transformer.from_crs(4326, 32646, always_xy=True)
            self.index = STRtree([GeoPoint(*self.transform.transform(float(self.graph.nodes[n]['x']), float(self.graph.nodes[n]['y']))) for n in self.node_ids])
            self.edge_shapes = [__import__('shapely').geometry.LineString(edge_geometry(self.graph, *edge)) for edge in self.edges.values()]
            self.edge_ids = list(self.edges)
            self.road_index = STRtree(self.edge_shapes)
            identity = [(n, self.graph.nodes[n]['x'], self.graph.nodes[n]['y']) for n in self.graph]
            identity.extend((i, self.graph[u][v][k]['length'], self.edge_shapes[j].wkt) for j, (i, (u, v, k)) in enumerate(self.edges.items()))
            self.dataset_id = hashlib.sha256(repr(identity).encode()).hexdigest()[:16]
            places_path = self.data_dir / 'places.json'
            if places_path.exists():
                places = json.loads(places_path.read_text(encoding='utf-8'))
                seen = set()
                for place in places:
                    if place['id'] in seen or not place.get('name') or not valid_coordinate([place['lon'], place['lat']]):
                        continue
                    seen.add(place['id'])
                    place['_search'] = ' '.join(str(place.get(k, '')) for k in ['name', 'name_en', 'name_bn', 'alt_names', 'locality']).casefold()
                    self.places.append(place)
            metadata_path = self.data_dir / 'metadata.json'
            if metadata_path.exists():
                self.metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
        except Exception as exc:
            self.graph = None
            self.error = f'Dataset loading failed: {exc}'

    def ready(self):
        if self.graph is None:
            raise RuntimeError(self.error or 'Dataset unavailable')

    def scenarios(self):
        with self.store.lock:
            custom = self.store.values('scenario')
            return {**{key: val.model_dump() for key, val in BUILTINS.items()}, **custom}

    def snapshot(self, scenario_id):
        self.ready()
        with self.store.lock:
            definitions = self.scenarios()
            if scenario_id not in definitions:
                raise KeyError('Scenario not found')
            scenario = Scenario.model_validate(definitions[scenario_id])
            overrides, revision = self.store.values('override'), self.store.revision()
        costs, conditions = {}, {}
        weights = scenario.weights.model_dump()
        ratio = float('inf')
        circle_center = GeoPoint(*self.transform.transform(scenario.area.lon, scenario.area.lat)) if scenario.scope == 'circle' else None
        for identifier, (u, v, k) in self.edges.items():
            attrs = self.graph[u][v][k]
            classes = attrs.get('highway', [])
            classes = classes if isinstance(classes, list) else [classes]
            applies = scenario.scope == 'network' and (not scenario.road_classes or bool(set(classes) & set(scenario.road_classes)))
            if circle_center is not None:
                line = LineString([self.transform.transform(lon, lat) for lon, lat in edge_geometry(self.graph, u, v, k)])
                applies = line.distance(circle_center) <= scenario.area.radius_m
            condition = scenario.conditions.model_dump() if applies else Conditions().model_dump()
            if scenario.scope != 'circle' and identifier in scenario.edges:
                condition = scenario.edges[identifier].model_dump()
            if identifier in overrides:
                condition = overrides[identifier]
            conditions[identifier] = condition
            cost = None if condition['blocked'] else float(attrs['length']) / 1000 * (1 + sum(weights[name] * condition[name] for name in weights))
            costs[identifier] = cost
            if cost is not None:
                distance = haversine([self.graph.nodes[u]['x'], self.graph.nodes[u]['y']], [self.graph.nodes[v]['x'], self.graph.nodes[v]['y']]) / 1000
                if distance > 0:
                    ratio = min(ratio, cost / distance)
        ratio = 0 if ratio == float('inf') else max(0, ratio * (1 - 1e-12))
        digest = hashlib.sha256(json.dumps([self.dataset_id, scenario_id, definitions[scenario_id], overrides, revision], sort_keys=True).encode()).hexdigest()[:16]
        return MappingProxyType(costs), MappingProxyType(conditions), scenario, revision, digest, ratio

    def route(self, query, snapshot=None):
        costs, conditions, scenario, revision, digest, ratio = snapshot or self.snapshot(query.scenario)
        if query.start not in self.graph or query.destination not in self.graph:
            raise ValueError('Unknown start or destination road node')
        limits = Limits(query.max_expansions, query.max_depth, query.timeout_seconds, query.trace_limit)
        goal = self.graph.nodes[query.destination]
        heuristic = lambda n: ratio * haversine([self.graph.nodes[n]['x'], self.graph.nodes[n]['y']], [goal['x'], goal['y']]) / 1000
        cost = lambda u, v, k, attrs: costs[edge_id(u, v, k)]
        names = list(ALGORITHMS) if query.algorithm == 'all' else [query.algorithm]
        results = []
        for name in names:
            result = ALGORITHMS[name](self.graph, query.start, query.destination, cost, limits, heuristic)
            result['geometry'] = route_geometry(self.graph, result['edges'])
            result['trace_points'] = [[self.graph.nodes[n]['x'], self.graph.nodes[n]['y']] for n in result['trace']]
            result['snapshot'] = digest
            if name == 'A*' and query.zero_heuristic_comparison:
                zero = ALGORITHMS[name](self.graph, query.start, query.destination, cost, limits)
                result['zero_heuristic'] = {k: zero[k] for k in ['status', 'cost', 'expanded', 'execution_ms']}
            results.append(result)
        return {'results': results, 'scenario': query.scenario, 'scenario_name': scenario.name, 'revision': revision, 'snapshot': digest, 'simulated': True, 'heuristic_cost_per_km': ratio}

    def snap(self, lat, lon, max_distance):
        self.ready()
        point = GeoPoint(*self.transform.transform(lon, lat))
        node = self.node_ids[int(self.index.nearest(point))]
        attrs = self.graph.nodes[node]
        distance = haversine([lon, lat], [attrs['x'], attrs['y']])
        if distance > max_distance:
            raise ValueError(f'Nearest road node is {distance:.0f} m away; maximum is {max_distance:.0f} m')
        return {'node': node, 'lat': attrs['y'], 'lon': attrs['x'], 'distance_m': distance}

    def stats(self):
        with self.store.lock:
            revision = self.store.revision()
        return {'ready': self.graph is not None, 'error': self.error, 'nodes': self.graph.number_of_nodes() if self.graph is not None else 0, 'edges': self.graph.number_of_edges() if self.graph is not None else 0, 'places': len(self.places), 'categories': dict(Counter(p['category'] for p in self.places)), 'metadata': self.metadata, 'revision': revision, 'simulated': True}

    def road(self, identifier, snapshot):
        if identifier not in self.edges:
            raise KeyError('Road edge not found')
        u, v, key = self.edges[identifier]
        attrs = self.graph[u][v][key]
        return {'type': 'Feature', 'geometry': {'type': 'LineString', 'coordinates': edge_geometry(self.graph, u, v, key)}, 'properties': {'id': identifier, 'u': u, 'v': v, 'key': key, 'name': attrs.get('name'), 'highway': attrs.get('highway'), 'osmid': attrs.get('osmid'), 'oneway': attrs.get('oneway'), 'length_m': attrs['length'], 'conditions': snapshot[1][identifier], 'cost': snapshot[0][identifier]}}
