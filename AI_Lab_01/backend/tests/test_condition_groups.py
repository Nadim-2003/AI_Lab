import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient
from backend.app.main import create_app
from backend.app.models import Scenario
from backend.app.service import Service


def mixed_scenario(service):
    ids = {edge: identifier for identifier, edge in service.edges.items()}
    return Scenario(name='Mixed conditions', scope='groups', weights={'traffic': 4, 'rain': 3, 'condition': 2}, groups=[
        {'target': 'classes', 'road_classes': ['primary'], 'conditions': {'traffic': 1}},
        {'target': 'circle', 'area': {'lat': 23.77, 'lon': 90.401, 'radius_m': 50}, 'conditions': {'rain': 1}},
        {'target': 'roads', 'road_ids': [ids[('s', 'b', '0')], ids[('b', 't', '0')]], 'conditions': {'condition': 1}},
    ]), ids


def test_mixed_targets_use_shared_weights_and_merge_overlaps(tmp_path, graph):
    service = Service(tmp_path, graph)
    scenario, ids = mixed_scenario(service)
    service.store.put('scenario', 'mixed', scenario.model_dump())
    costs, conditions, *_ = service.snapshot('mixed')
    assert costs[ids[('s', 'b', '0')]] == pytest.approx(.210 * (1 + 3 + 2))
    assert costs[ids[('b', 't', '0')]] == pytest.approx(.210 * (1 + 2))
    assert costs[ids[('a', 's', '0')]] == pytest.approx(.160 * (1 + 4))
    assert costs[ids[('a', 't', '0')]] == pytest.approx(.240)
    scenario.groups.append(scenario.groups[1].model_copy(deep=True))
    service.store.put('scenario', 'mixed', scenario.model_dump())
    assert service.snapshot('mixed')[0] == costs
    scenario.groups[2].conditions.blocked = True
    service.store.put('scenario', 'mixed', scenario.model_dump())
    assert service.snapshot('mixed')[0][ids[('s', 'b', '0')]] is None
    service.store.put('override', ids[('s', 'b', '0')], {'traffic': 0, 'condition': 0, 'rain': 0, 'safety': 0, 'blocked': False})
    assert service.snapshot('mixed')[0][ids[('s', 'b', '0')]] == pytest.approx(.210)


@pytest.mark.parametrize('groups', [[], [{'target': 'circle'}], [{'target': 'roads'}], [{'target': 'classes'}] * 21])
def test_invalid_groups_are_rejected(groups):
    with pytest.raises(ValidationError):
        Scenario(name='Invalid groups', scope='groups', groups=groups)


def test_mixed_groups_roundtrip_and_reject_unknown_roads(tmp_path, graph):
    app = create_app(tmp_path, graph)
    client = TestClient(app)
    scenario, _ = mixed_scenario(app.state.service)
    response = client.post('/api/scenarios', json=scenario.model_dump())
    assert response.status_code == 201
    identifier = response.json()['id']
    saved = next(item for item in client.get('/api/scenarios').json() if item['id'] == identifier)
    assert saved['groups'] == response.json()['groups']
    assert saved['weights'] == response.json()['weights']
    response = client.post('/api/routes', json={'start': 's', 'destination': 't', 'scenario': identifier, 'algorithm': 'UCS'})
    assert response.status_code == 200
    assert response.json()['results'][0]['found']
    scenario.groups[2].road_ids = ['missing-edge']
    assert client.post('/api/scenarios', json=scenario.model_dump()).status_code == 422
