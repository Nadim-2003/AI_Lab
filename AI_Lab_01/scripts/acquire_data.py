import argparse
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import hashlib
import json
import math
import re
import time
from urllib.parse import urlsplit
import geopandas as gpd
import requests
from osmnx._errors import ResponseStatusCodeError, InsufficientResponseError
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


class AcquisitionError(RuntimeError):
    pass


class TemporaryOverpassError(AcquisitionError):
    def __init__(self, message, retry_after=0):
        super().__init__(message)
        self.retry_after = retry_after


def check_overpass_response(response, *args, **kwargs):
    if not urlsplit(response.url).path.rstrip('/').endswith('/interpreter'):
        return response
    if response.status_code in {429, 500, 502, 503, 504}:
        retry_after = response.headers.get('Retry-After', '0')
        try:
            delay = max(0, float(retry_after))
        except ValueError:
            try:
                delay = max(0, (parsedate_to_datetime(retry_after) - datetime.now(timezone.utc)).total_seconds())
            except (ValueError, TypeError, OverflowError):
                delay = 0
        response.close()
        raise TemporaryOverpassError(f'Overpass returned HTTP {response.status_code}', delay if math.isfinite(delay) else 0)
    if response.ok:
        try:
            payload = response.json()
        except ValueError:
            return response
        if isinstance(payload, dict) and payload.get('remark'):
            response.close()
            raise TemporaryOverpassError('Overpass returned a remark indicating potentially incomplete results; this response will not be saved.')
    return response


def pause_download(seconds):
    while seconds > 0:
        interval = min(seconds, 60)
        time.sleep(interval)
        seconds -= interval


def retry_download(operation, label, attempts=4, retry_delay=10):
    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except (requests.ConnectionError, requests.Timeout, ResponseStatusCodeError, TemporaryOverpassError) as exc:
            transient = isinstance(exc, (requests.ConnectionError, requests.Timeout, TemporaryOverpassError)) or re.search(r"\b(?:429|500|502|503|504)\b", str(exc))
            if not transient:
                raise
            if attempt == attempts:
                raise AcquisitionError(f'{label} failed after {attempts} attempts. The OSM server may be busy or unreachable. Completed downloads are retained; rerun the same command later to resume.') from exc
            delay = max(min(60, retry_delay * 2 ** (attempt - 1)), getattr(exc, 'retry_after', 0))
            print(f'{label}: temporary server/network failure; retry {attempt + 1}/{attempts} in {delay:g} seconds.', flush=True)
            pause_download(delay)


def save_json(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, default=str), encoding='utf-8')
    temporary.replace(path)


def load_graph_checkpoint(boundary, checkpoint, args):
    graph_path = checkpoint / 'dhaka.graphml'
    manifest_path = checkpoint / 'graph.json'
    if graph_path.exists() and manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        if hashlib.sha256(graph_path.read_bytes()).hexdigest() != manifest['sha256']:
            raise AcquisitionError(f'Graph checkpoint checksum mismatch: {graph_path}. Preserve it for diagnosis, then remove this checkpoint directory before retrying.')
        print('Resuming saved road graph; no new graph request needed.', flush=True)
        return ox.load_graphml(graph_path), manifest['retrieved_at']
    if getattr(args, 'publish_partial', False):
        raise AcquisitionError('No verified graph checkpoint exists for these study bounds and server. Run setup_data.bat first; offline recovery never downloads data.')
    print('Retrieving directed driving graph for explicit study rectangle', flush=True)
    graph = retry_download(lambda: ox.graph_from_polygon(boundary, network_type='drive', retain_all=True, simplify=True), 'Road graph', args.attempts, args.retry_delay)
    temporary = checkpoint / 'dhaka.pending.graphml'
    ox.save_graphml(graph, temporary)
    temporary.replace(graph_path)
    retrieved_at = datetime.now(timezone.utc).isoformat()
    save_json(manifest_path, {'retrieved_at': retrieved_at, 'sha256': hashlib.sha256(graph_path.read_bytes()).hexdigest()})
    return graph, retrieved_at


def download_place_tiles(boundary, checkpoint, args):
    west, south, east, north = boundary.bounds
    frames, timestamps = [], []
    total = args.place_grid ** 2
    for row in range(args.place_grid):
        for column in range(args.place_grid):
            index = row * args.place_grid + column
            path = checkpoint / f'places-{args.place_grid}-{index}.json'
            label = f'Places tile {index + 1}/{total}'
            if path.exists():
                print(f'{label}: using completed checkpoint.', flush=True)
                payload = json.loads(path.read_text(encoding='utf-8'))
            elif getattr(args, 'publish_partial', False):
                print(f'{label}: not downloaded; recording incomplete place coverage.', flush=True)
                timestamps.append(None)
                continue
            else:
                tile = box(west + (east - west) * column / args.place_grid, south + (north - south) * row / args.place_grid, west + (east - west) * (column + 1) / args.place_grid, south + (north - south) * (row + 1) / args.place_grid)
                print(f'{label}: retrieving named OSM features.', flush=True)
                try:
                    frame = retry_download(lambda: ox.features_from_polygon(tile, tags={'name': True, 'name:en': True, 'name:bn': True}), label, args.attempts, args.retry_delay)
                except InsufficientResponseError as exc:
                    if 'No matching features' not in str(exc):
                        raise
                    frame = None
                if frame is None or frame.empty:
                    feature_list = []
                else:
                    export = frame.copy()
                    export.index = export.index.set_names(['source_type', 'source_id'])
                    feature_list = json.loads(export.reset_index().to_json(drop_id=True, default=str))['features']
                payload = {'retrieved_at': datetime.now(timezone.utc).isoformat(), 'features': feature_list}
                save_json(path, payload)
                if index + 1 < total:
                    time.sleep(args.request_pause)
            timestamps.append(payload['retrieved_at'])
            if payload['features']:
                frame = gpd.GeoDataFrame.from_features(payload['features'], crs='EPSG:4326').set_index(['source_type', 'source_id'])
                frames.append(frame)
    if not frames:
        empty = gpd.GeoDataFrame(geometry=[], crs='EPSG:4326')
        empty.index = pd.MultiIndex.from_tuples([], names=['source_type', 'source_id'])
        return empty, timestamps
    return gpd.GeoDataFrame(pd.concat(frames), crs='EPSG:4326'), timestamps


def main():
    parser = argparse.ArgumentParser(description='Acquire actual OpenStreetMap driving roads and named features inside an explicit Dhaka study rectangle.')
    parser.add_argument('--bbox', nargs=4, type=float, default=[90.30, 23.65, 90.50, 23.90], metavar=('WEST', 'SOUTH', 'EAST', 'NORTH'))
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1] / 'data')
    parser.add_argument('--replace', action='store_true')
    parser.add_argument('--publish-partial', action='store_true', help='Install the verified saved graph and available place tiles without any network requests; mark incomplete place coverage explicitly.')
    parser.add_argument('--place-grid', type=int, default=3, help='Split place acquisition into N by N sequential requests (default: 3).')
    parser.add_argument('--attempts', type=int, default=4)
    parser.add_argument('--retry-delay', type=float, default=10)
    parser.add_argument('--request-pause', type=float, default=2)
    parser.add_argument('--overpass-url', default='https://overpass-api.de/api', help='HTTPS Overpass base URL; use only a service you are authorized to access.')
    args = parser.parse_args()
    west, south, east, north = args.bbox
    if not 89 <= west < east <= 92 or not 22 <= south < north <= 25:
        parser.error('Expected an explicit Dhaka-region bounding box')
    if not 1 <= args.place_grid <= 10 or not 1 <= args.attempts <= 8:
        parser.error('--place-grid must be 1..10 and --attempts must be 1..8')
    if not all(math.isfinite(value) and 0 <= value <= 60 for value in [args.retry_delay, args.request_pause]):
        parser.error('Retry delay and request pause must be finite values between 0 and 60 seconds')
    endpoint = urlsplit(args.overpass_url)
    if endpoint.scheme != 'https' or not endpoint.hostname or endpoint.username or endpoint.password or endpoint.query or endpoint.fragment:
        parser.error('--overpass-url must be an HTTPS base URL without credentials, query, or fragment')
    args.output.mkdir(parents=True, exist_ok=True)
    existing = [args.output / name for name in ['dhaka.graphml', 'roads.geojson', 'places.json', 'metadata.json'] if (args.output / name).exists()]
    if existing and not args.replace:
        parser.error('Dataset exists. Use --replace to preserve a backup and replace it explicitly.')
    ox.settings.overpass_url = args.overpass_url.rstrip('/')
    hooks = dict(ox.settings.requests_kwargs.get('hooks', {}))
    previous = hooks.get('response', [])
    previous = [previous] if callable(previous) else list(previous)
    hooks['response'] = [check_overpass_response, *[hook for hook in previous if hook is not check_overpass_response]]
    ox.settings.requests_kwargs = {**ox.settings.requests_kwargs, 'hooks': hooks}
    ox.settings.use_cache = True
    ox.settings.cache_folder = str(args.output / 'osm-cache')
    ox.settings.requests_timeout = 180
    ox.settings.http_user_agent = 'DhakaRouteLab/1.0 university research; OSMnx'
    boundary = box(west, south, east, north)
    checkpoint_id = hashlib.sha256(json.dumps([args.bbox, ox.settings.overpass_url, 'drive-v1']).encode()).hexdigest()[:16]
    checkpoint = args.output / 'download-checkpoints' / checkpoint_id
    checkpoint.mkdir(parents=True, exist_ok=True)
    graph, road_retrieved_at = load_graph_checkpoint(boundary, checkpoint, args)
    print(f'Retrieved {len(graph)} nodes, {graph.number_of_edges()} directed edges', flush=True)
    with tempfile.TemporaryDirectory(prefix='acquisition-', dir=args.output) as temporary:
        stage = Path(temporary)
        ox.save_graphml(graph, stage / 'dhaka.graphml')
        service = Service(stage)
        with closing(service.store.db):
            service.ready()
            print('Retrieving named OSM features', flush=True)
            features, tile_timestamps = download_place_tiles(boundary, checkpoint, args)
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
        metadata = {'source': 'OpenStreetMap contributors', 'license': 'ODbL 1.0', 'retrieved_at': datetime.now(timezone.utc).isoformat(), 'road_retrieved_at': road_retrieved_at, 'place_tile_retrieved_at': tile_timestamps, 'overpass_url': ox.settings.overpass_url, 'place_grid': args.place_grid, 'places_complete': all(stamp is not None for stamp in tile_timestamps), 'completed_place_tiles': sum(stamp is not None for stamp in tile_timestamps), 'total_place_tiles': len(tile_timestamps), 'missing_place_tiles': [i + 1 for i, stamp in enumerate(tile_timestamps) if stamp is None], 'network_type': 'drive', 'study_area': {'description': 'Explicit configurable Dhaka study rectangle; not an administrative boundary', 'bbox': args.bbox, 'geometry': mapping(boundary)}, 'nodes': graph.number_of_nodes(), 'edges': graph.number_of_edges(), 'weak_components': __import__('networkx').number_weakly_connected_components(graph), 'unique_places': len(records), 'categories': dict(Counter(p['category'] for p in records)), 'quality_report': dict(rejected), 'graph_sha256': hashlib.sha256((stage / 'dhaka.graphml').read_bytes()).hexdigest()}
        (stage / 'metadata.json').write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding='utf-8')
        if existing:
            backup = args.output / ('backup-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f'))
            backup.mkdir()
            for path in existing:
                shutil.copy2(path, backup / path.name)
        for name in ['dhaka.graphml', 'roads.geojson', 'places.json', 'metadata.json']:
            (stage / name).replace(args.output / name)
        print(json.dumps(metadata, indent=2, ensure_ascii=False))
        if not metadata['places_complete']:
            print(f"Road graph installed. Place coverage is INCOMPLETE: {metadata['completed_place_tiles']}/{metadata['total_place_tiles']} tiles and {len(records)} valid places. Use map clicks for locations missing from search. Restart the backend now. Later rerun the normal acquisition command with --replace to resume missing tiles.", flush=True)
        if len(records) < 1000:
            print('WARNING: fewer than 1000 valid source records; inspect study area and quality_report. No artificial records were added.')


if __name__ == '__main__':
    try:
        main()
    except (AcquisitionError, requests.RequestException, ResponseStatusCodeError, InsufficientResponseError) as exc:
        print(f'Data acquisition stopped: {exc}', file=sys.stderr)
        print('Completed graph and place tiles remain in data/download-checkpoints. Wait before rerunning the same command, or use setup_data.bat --publish-partial to install the saved graph and completed tiles offline. Existing dataset files were not replaced by this failed download.', file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print('Download interrupted. Completed checkpoints are retained for the next run.', file=sys.stderr)
        sys.exit(130)
