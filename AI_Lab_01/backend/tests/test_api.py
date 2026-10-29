import json
import networkx as nx
import pytest
from fastapi.testclient import TestClient
from backend.app.main import create_app
from backend.app.models import RouteQuery, Conditions
from backend.app.service import Service, BUILTINS


@pytest.fixture
def client(tmp_path, graph):
    return TestClient(create_app(tmp_path, graph))


def query(**changes):
    return {'start': 's', 'destination': 't', 'algorithm': 'all', **changes}


def test_health_missing_dataset(tmp_path):
    client = TestClient(create_app(tmp_path))
    assert client.get('/api/health').json()['status'] == 'alive'
    assert client.get('/api/ready').status_code == 503
    response = client.post('/api/routes', json=query())
    assert response.status_code == 503
    assert 'missing' in response.json()['detail'].lower()


def test_all_same_snapshot_and_heuristic(client):
    response = client.post('/api/routes', json=query())
    assert response.status_code == 200, response.text
    result = response.json()
    assert len(result['results']) == 5
    assert len({r['snapshot'] for r in result['results']}) == 1
    ucs, astar = result['results'][3:]
    assert astar['cost'] == pytest.approx(ucs['cost'])
    assert astar['cost'] == pytest.approx(astar['zero_heuristic']['cost'])
    assert astar['geometry']['coordinates'][1] == [90.4004, 23.7708]
    assert astar['trace_points'][0] == [90.4, 23.77]


def test_blocking_reverse_and_restore(client):
    baseline = client.post('/api/routes', json=query(algorithm='UCS')).json()
    identifier = 's:a:curve'
    assert client.put('/api/overrides', params={'id': identifier}, json={'blocked': True}).status_code == 200
    changed = client.post('/api/routes', json=query(algorithm='UCS')).json()
    assert ['s', 'a', 'curve'] not in changed['results'][0]['edges']
    assert changed['snapshot'] != baseline['snapshot']
    reverse = client.get('/api/road', params={'id': 'a:s:0'}).json()
    assert not reverse['properties']['conditions']['blocked']
    client.delete('/api/overrides', params={'id': identifier})
    restored = client.post('/api/routes', json=query(algorithm='UCS')).json()
    assert restored['results'][0]['edges'] == baseline['results'][0]['edges']
    for identifier in ['a:t:0', 'b:t:0']:
        client.put('/api/overrides', params={'id': identifier}, json={'blocked': True})
    result = client.post('/api/routes', json=query()).json()
    assert all(not r['found'] and r['geometry'] is None for r in result['results'])
    client.delete('/api/overrides')
    assert client.post('/api/routes', json=query()).json()['results'][0]['found']


def test_condition_cost_and_snapshot_isolation(client):
    service = client.app.state.service
    snap = service.snapshot('normal')
    before = service.route(RouteQuery(**query(algorithm='UCS')), snap)
    client.put('/api/overrides', params={'id': 's:a:curve'}, json={'traffic': 1, 'safety': 1})
    held = service.route(RouteQuery(**query(algorithm='UCS')), snap)
    assert held['snapshot'] == before['snapshot']
    assert held['results'][0]['cost'] == before['results'][0]['cost']
    assert service.snapshot('normal')[0]['s:a:curve'] > snap[0]['s:a:curve']
    assert service.graph['s']['a']['curve']['length'] == 160


def test_all_scenarios_custom_persistence_and_precedence(client, tmp_path, graph):
    scenarios = client.get('/api/scenarios').json()
    assert len(scenarios) == 6
    response = client.post('/api/compare-scenarios', json={'query': query(algorithm='UCS'), 'scenarios': list(BUILTINS)})
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 6
    assert all(r['results'][0]['found'] for r in results)
    normal = client.get('/api/road', params={'id': 's:a:curve'}).json()['properties']['cost']
    traffic = client.get('/api/road', params={'id': 's:a:curve', 'scenario': 'traffic'}).json()['properties']['cost']
    assert traffic > normal
    custom = {'name': 'Test closure', 'edges': {'s:a:curve': {'blocked': True}}}
    created = client.post('/api/scenarios', json=custom)
    assert created.status_code == 201, created.text
    identifier = created.json()['id']
    loaded = Service(tmp_path, graph)
    assert identifier in loaded.scenarios()
    assert loaded.snapshot(identifier)[0]['s:a:curve'] is None
    client.put('/api/overrides', params={'id': 's:a:curve'}, json={'blocked': False})
    assert loaded.snapshot(identifier)[0]['s:a:curve'] is not None
    assert client.put(f'/api/scenarios/{identifier}', json={'name': 'Updated'}).status_code == 200
    assert client.delete(f'/api/scenarios/{identifier}').status_code == 200
    assert client.delete('/api/scenarios/normal').status_code == 409
    assert client.post('/api/scenarios', json={'name': 'Bad', 'edges': {'bad:id:0': {}}}).status_code == 422


def test_snapping_validation_roads(client):
    response = client.post('/api/resolve', json={'lat': 23.77, 'lon': 90.4})
    assert response.status_code == 200
    assert response.json()['node'] == 's'
    assert client.post('/api/resolve', json={'lat': 24.8, 'lon': 90.4}).status_code == 422
    assert client.post('/api/resolve', json={'lat': 100, 'lon': 90}).status_code == 422
    assert client.post('/api/routes', json=query(algorithm='BAD')).status_code == 422
    assert client.post('/api/routes', json=query(start='unknown')).status_code == 422
    assert client.put('/api/overrides', params={'id': 's:a:curve'}, json={'traffic': 2}).status_code == 422
    roads = client.get('/api/roads', params={'limit': 1}).json()
    assert roads['truncated'] and len(roads['features']) == 1
    assert client.get('/api/road', params={'id': 'unknown'}).status_code == 404


def test_places_dedupe_bangla_and_search(tmp_path, graph):
    records = [{'id': 'node/1', 'name': 'ঢাকা University', 'name_en': 'Dhaka University', 'category': 'amenity:university', 'lon': 90.4, 'lat': 23.77}, {'id': 'node/2', 'name': 'Invalid', 'category': 'other', 'lon': 200, 'lat': 23.77}]
    (tmp_path / 'places.json').write_text(json.dumps(records + [records[0]]))
    client = TestClient(create_app(tmp_path, graph))
    assert client.get('/api/metadata').json()['places'] == 1
    assert len(client.get('/api/places', params={'q': 'DHAKA'}).json()) == 1
    assert len(client.get('/api/places', params={'q': 'ঢাকা'}).json()) == 1
    assert client.get('/api/places', params={'q': 'xyz'}).json() == []
    assert client.get('/api/places/node%2F1').json()['id'] == 'node/1'


def test_invalid_graph(tmp_path):
    service = Service(tmp_path, nx.Graph())
    assert not service.stats()['ready']
    assert 'directed' in service.error


def test_dataset_endpoints_explain_missing_data_without_false_readiness(tmp_path):
    client = TestClient(create_app(tmp_path))
    metadata = client.get('/api/metadata')
    assert metadata.status_code == 200 and not metadata.json()['ready']
    for path in ['/api/roads', '/api/places?q=dhaka', '/api/ready']:
        response = client.get(path)
        assert response.status_code == 503
        assert 'scripts/acquire_data.py' in response.json()['detail']
