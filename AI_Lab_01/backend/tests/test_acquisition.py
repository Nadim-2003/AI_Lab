import json
import sys
from types import SimpleNamespace
from unittest.mock import Mock
import requests
from osmnx._errors import ResponseStatusCodeError
import geopandas as gpd
import networkx as nx
import pandas as pd
import pytest
from shapely.geometry import Point
from scripts import acquire_data
from backend.app.service import Service


def test_pipeline_saves_loadable_dataset_and_cleans_staging(tmp_path, graph, monkeypatch):
    converted = nx.convert_node_labels_to_integers(graph, first_label=1)
    numeric = nx.MultiDiGraph(crs='EPSG:4326')
    numeric.add_nodes_from(converted.nodes(data=True))
    for u, v, key, attrs in converted.edges(keys=True, data=True):
        numeric.add_edge(u, v, key=int(attrs['osmid']), **attrs)
    features = gpd.GeoDataFrame({'name': ['Test source feature', '', 'Outside feature'], 'amenity': ['university', 'school', 'hospital'], 'geometry': [Point(90.4, 23.77), Point(90.4, 23.77), Point(91, 24)]}, index=pd.MultiIndex.from_tuples([('node', 1), ('node', 2), ('node', 3)]), crs='EPSG:4326')
    monkeypatch.setattr(acquire_data.time, 'sleep', lambda _: None)
    graph_download = Mock(return_value=numeric)
    monkeypatch.setattr(acquire_data.ox, 'graph_from_polygon', graph_download)
    monkeypatch.setattr(acquire_data.ox, 'features_from_polygon', lambda *args, **kwargs: features)
    monkeypatch.setattr(sys, 'argv', ['acquire_data.py', '--output', str(tmp_path)])
    acquire_data.main()
    service = Service(tmp_path)
    try:
        assert service.stats()['ready']
        assert len(service.places) == 1
        assert service.places[0]['node'] is not None
    finally:
        service.store.db.close()
    metadata = json.loads((tmp_path / 'metadata.json').read_text())
    assert metadata['unique_places'] == 1
    assert metadata['quality_report']['missing_name'] == 1
    assert metadata['quality_report']['invalid_or_outside_coordinate'] == 1
    assert len(json.loads((tmp_path / 'roads.geojson').read_text())['features']) == 6
    assert not list(tmp_path.glob('acquisition-*'))
    original = (tmp_path / 'dhaka.graphml').read_bytes()
    with pytest.raises(SystemExit):
        acquire_data.main()
    monkeypatch.setattr(sys, 'argv', ['acquire_data.py', '--output', str(tmp_path), '--replace'])
    acquire_data.main()
    backups = list(tmp_path.glob('backup-*'))
    assert len(backups) == 1
    assert (backups[0] / 'dhaka.graphml').read_bytes() == original
    assert graph_download.call_count == 1


def test_busy_server_retries_with_exponential_backoff(monkeypatch):
    sleep = Mock()
    monkeypatch.setattr(acquire_data.time, 'sleep', sleep)
    operation = Mock(side_effect=[ResponseStatusCodeError('responded: 502 Bad Gateway'), requests.Timeout('timed out'), 'downloaded'])
    assert acquire_data.retry_download(operation, 'Places', attempts=4) == 'downloaded'
    assert [call.args[0] for call in sleep.call_args_list] == [10, 20]
    assert operation.call_count == 3


def test_retries_are_bounded_and_access_denials_are_not_retried(monkeypatch):
    sleep = Mock()
    monkeypatch.setattr(acquire_data.time, 'sleep', sleep)
    operation = Mock(side_effect=ResponseStatusCodeError('responded: 502 Bad Gateway'))
    with pytest.raises(acquire_data.AcquisitionError, match='3 attempts'):
        acquire_data.retry_download(operation, 'Places', attempts=3)
    assert operation.call_count == 3
    denied = Mock(side_effect=ResponseStatusCodeError('responded: 403 Forbidden'))
    with pytest.raises(ResponseStatusCodeError):
        acquire_data.retry_download(denied, 'Places')
    assert denied.call_count == 1


def response(status, payload, headers=None):
    result = requests.Response()
    result.url = 'https://overpass-api.de/api/interpreter'
    result.status_code = status
    result._content = json.dumps(payload).encode()
    result._content_consumed = True
    result.headers.update(headers or {})
    return result


def test_response_hook_honors_retry_after_and_rejects_incomplete_results(monkeypatch):
    sleep = Mock()
    monkeypatch.setattr(acquire_data.time, 'sleep', sleep)
    calls = [response(503, {}, {'Retry-After': '30'}), response(200, {'elements': []})]
    result = acquire_data.retry_download(lambda: acquire_data.check_overpass_response(calls.pop(0)), 'Tile')
    assert result.json() == {'elements': []}
    sleep.assert_called_once_with(30)
    with pytest.raises(acquire_data.TemporaryOverpassError, match='incomplete'):
        acquire_data.check_overpass_response(response(200, {'elements': [], 'remark': 'runtime error: Query timed out'}))
    allowed = response(200, {'elements': []})
    assert acquire_data.check_overpass_response(allowed) is allowed


def test_place_tiles_resume_after_interruption(tmp_path, monkeypatch):
    args = SimpleNamespace(place_grid=2, attempts=1, retry_delay=0, request_pause=0)
    frame = gpd.GeoDataFrame({'name': ['Real source fixture'], 'geometry': [Point(90.4, 23.77)]}, index=pd.MultiIndex.from_tuples([('node', 1)]), crs='EPSG:4326')
    download = Mock(side_effect=[frame, ResponseStatusCodeError('responded: 502 Bad Gateway')])
    monkeypatch.setattr(acquire_data.ox, 'features_from_polygon', download)
    with pytest.raises(acquire_data.AcquisitionError):
        acquire_data.download_place_tiles(acquire_data.box(90.3, 23.65, 90.5, 23.9), tmp_path, args)
    assert (tmp_path / 'places-2-0.json').exists()
    assert not (tmp_path / 'places-2-1.json').exists()
    download = Mock(return_value=frame)
    monkeypatch.setattr(acquire_data.ox, 'features_from_polygon', download)
    data, timestamps = acquire_data.download_place_tiles(acquire_data.box(90.3, 23.65, 90.5, 23.9), tmp_path, args)
    assert download.call_count == 3
    assert len(data) == 4 and len(timestamps) == 4
    assert all(index == ('node', 1) for index in data.index)
