import json
import sys
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
    monkeypatch.setattr(acquire_data.ox, 'graph_from_polygon', lambda *args, **kwargs: numeric)
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
