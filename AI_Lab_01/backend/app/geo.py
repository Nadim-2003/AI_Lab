from math import asin, cos, radians, sin, sqrt, isfinite
from shapely.geometry import LineString
from shapely import wkt


def haversine(a, b):
    lat1, lat2 = radians(a[1]), radians(b[1])
    value = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin(radians(b[0] - a[0]) / 2) ** 2
    return 6371009 * 2 * asin(min(1, sqrt(value)))


def valid_coordinate(point):
    return len(point) >= 2 and all(isfinite(x) for x in point[:2]) and -180 <= point[0] <= 180 and -90 <= point[1] <= 90


def edge_geometry(graph, u, v, key):
    attrs = graph[u][v][key]
    geometry = attrs.get('geometry')
    if isinstance(geometry, str):
        geometry = wkt.loads(geometry)
    start = [float(graph.nodes[u]['x']), float(graph.nodes[u]['y'])]
    end = [float(graph.nodes[v]['x']), float(graph.nodes[v]['y'])]
    if geometry is None:
        coords = [start, end]
    elif isinstance(geometry, LineString):
        coords = [list(point[:2]) for point in geometry.coords]
    else:
        raise ValueError('Road geometry must be a LineString')
    if len(coords) < 2 or not all(valid_coordinate(p) for p in coords):
        raise ValueError('Invalid road geometry coordinates')
    if haversine(start, coords[-1]) + haversine(end, coords[0]) < haversine(start, coords[0]) + haversine(end, coords[-1]):
        coords.reverse()
    return coords


def route_geometry(graph, edges):
    result = []
    for u, v, key in edges:
        segment = edge_geometry(graph, u, v, key)
        result.extend(segment[1:] if result and result[-1] == segment[0] else segment)
    return {'type': 'LineString', 'coordinates': result} if result else None
