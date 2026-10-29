import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import osmnx as ox
import pandas as pd
from shapely.geometry import box, mapping

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.service import Service
from backend.app.geo import valid_coordinate


def clean(value):
    if isinstance(value, (list, tuple)):
        return '; '.join(str(v) for v in value)
    return '' if value is None or (isinstance(value, float) and pd.isna(value)) else str(value)


def category(row):
    for tag in ['amenity', 'shop', 'tourism', 'leisure', 'railway', 'public_transport', 'place', 'highway', 'office', 'building']:
        value = clean(row.get(tag))
        if value:
            return f'{tag}:{value}'
    return 'other'


def main():
    parser = argparse.ArgumentParser(description='Acquire actual OpenStreetMap driving roads and named features inside an explicit Dhaka study rectangle.')
    parser.add_argument('--bbox', nargs=4, type=float, default=[90.30, 23.65, 90.50, 23.90], metavar=('WEST', 'SOUTH', 'EAST', 'NORTH'))
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1] / 'data')
    parser.add_argument('--replace', action='store_true')
    args = parser.parse_args()
    west, south, east, north = args.bbox
    if not 89 <= west < east <= 92 or not 22 <= south < north <= 25:
        parser.error('Expected an explicit Dhaka-region bounding box')
    args.output.mkdir(parents=True, exist_ok=True)
    existing = [args.output / name for name in ['dhaka.graphml', 'roads.geojson', 'places.json', 'metadata.json'] if (args.output / name).exists()]
    if existing and not args.replace:
        parser.error('Dataset exists. Use --replace to preserve a backup and replace it explicitly.')
    ox.settings.use_cache = True
    ox.settings.cache_folder = str(args.output / 'osm-cache')
    ox.settings.requests_timeout = 180
    ox.settings.http_user_agent = 'DhakaRouteLab/1.0 university research; OSMnx'
    boundary = box(west, south, east, north)
    print('Retrieving directed driving graph for explicit study rectangle', flush=True)
    graph = ox.graph_from_polygon(boundary, network_type='drive', retain_all=True, simplify=True)
    print(f'Retrieved {len(graph)} nodes, {graph.number_of_edges()} directed edges', flush=True)
    with tempfile.TemporaryDirectory(prefix='acquisition-', dir=args.output) as temporary:
        stage = Path(temporary)
        ox.save_graphml(graph, stage / 'dhaka.graphml')
        service = Service(stage)
        service.ready()
        print('Retrieving named OSM features', flush=True)
        features = ox.features_from_polygon(boundary, tags={'name': True, 'name:en': True, 'name:bn': True})
        records, seen = [], set()
        rejected = Counter()
        for identity, row in features.iterrows():
            element, osm_id = identity
            identifier = f'{element}/{osm_id}'
            if identifier in seen:
                rejected['duplicates'] += 1
                continue
            seen.add(identifier)
            name = clean(row.get('name')) or clean(row.get('name:en')) or clean(row.get('name:bn'))
            if not name:
                rejected['missing_name'] += 1
                continue
            geometry = row.geometry
            if geometry is None or geometry.is_empty:
                rejected['missing_geometry'] += 1
                continue
            point = geometry.representative_point()
            lon, lat = point.x, point.y
            if not valid_coordinate([lon, lat]) or not boundary.covers(point):
                rejected['invalid_or_outside_coordinate'] += 1
                continue
            record = {'id': identifier, 'osm_type': element, 'osm_id': int(osm_id), 'name': name, 'name_en': clean(row.get('name:en')), 'name_bn': clean(row.get('name:bn')), 'alt_names': clean(row.get('alt_name')), 'category': category(row), 'lat': lat, 'lon': lon, 'locality': clean(row.get('addr:suburb')) or clean(row.get('addr:city')), 'address': ' '.join(filter(None, [clean(row.get('addr:housenumber')), clean(row.get('addr:street'))])), 'source': 'OpenStreetMap', 'node': None, 'snapping_distance_m': None}
            try:
                snapped = service.snap(lat, lon, 500)
                record['node'], record['snapping_distance_m'] = snapped['node'], snapped['distance_m']
            except ValueError:
                rejected['unresolved_road_match'] += 1
            records.append(record)
        (stage / 'places.json').write_text(json.dumps(records, ensure_ascii=False), encoding='utf-8')
        snapshot = service.snapshot('normal')
        roads = [service.road(identifier, snapshot) for identifier in service.edges]
        (stage / 'roads.geojson').write_text(json.dumps({'type': 'FeatureCollection', 'features': roads}), encoding='utf-8')
        metadata = {'source': 'OpenStreetMap contributors', 'license': 'ODbL 1.0', 'retrieved_at': datetime.now(timezone.utc).isoformat(), 'network_type': 'drive', 'study_area': {'description': 'Explicit configurable Dhaka study rectangle; not an administrative boundary', 'bbox': args.bbox, 'geometry': mapping(boundary)}, 'nodes': graph.number_of_nodes(), 'edges': graph.number_of_edges(), 'weak_components': __import__('networkx').number_weakly_connected_components(graph), 'unique_places': len(records), 'categories': dict(Counter(p['category'] for p in records)), 'quality_report': dict(rejected), 'graph_sha256': hashlib.sha256((stage / 'dhaka.graphml').read_bytes()).hexdigest()}
        (stage / 'metadata.json').write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding='utf-8')
        if existing:
            backup = args.output / ('backup-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f'))
            backup.mkdir()
            for path in existing:
                shutil.copy2(path, backup / path.name)
        for name in ['dhaka.graphml', 'roads.geojson', 'places.json', 'metadata.json']:
            (stage / name).replace(args.output / name)
        print(json.dumps(metadata, indent=2, ensure_ascii=False))
        if len(records) < 1000:
            print('WARNING: fewer than 1000 valid source records; inspect study area and quality_report. No artificial records were added.')


if __name__ == '__main__':
    main()
