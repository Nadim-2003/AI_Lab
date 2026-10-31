import pytest
from pydantic import ValidationError
from backend.app.models import Scenario
from backend.app.service import Service


def test_selected_scope_keeps_other_roads_normal(tmp_path, graph):
    service = Service(tmp_path, graph)
    selected, other = list(service.edges)[:2]
    scenario = Scenario(name='Local rain', scope='selected_roads', conditions={'rain': 1, 'blocked': True}, edges={selected: {'rain': 1}})
    service.store.put('scenario', 'local', scenario.model_dump())
    costs, conditions, *_ = service.snapshot('local')
    assert conditions[selected]['rain'] == 1
    assert conditions[other]['rain'] == 0
    assert conditions[other]['blocked'] is False
    assert costs[other] is not None
    service.store.put('override', other, {'traffic': 0, 'condition': 0, 'rain': 0, 'safety': 0, 'blocked': True})
    assert service.snapshot('local')[0][other] is None


def test_existing_scenarios_default_to_network():
    assert Scenario(name='Existing').scope == 'network'
    with pytest.raises(ValidationError):
        Scenario(name='Empty selection', scope='selected_roads')


def test_circle_matches_crossing_roads_and_resizes(tmp_path, graph):
    service = Service(tmp_path, graph)
    crossing = next(key for key, edge in service.edges.items() if edge == ('s', 'b', '0'))
    outside = next(key for key, edge in service.edges.items() if edge == ('b', 't', '0'))
    scenario = Scenario(name='Circle rain', scope='circle', area={'lat': 23.77, 'lon': 90.401, 'radius_m': 50}, conditions={'rain': 1}, edges={outside: {'blocked': True}})
    service.store.put('scenario', 'circle', scenario.model_dump())
    snapshot = service.snapshot('circle')
    assert snapshot[1][crossing]['rain'] == 1  # Both endpoints are outside, but the line crosses the circle.
    assert snapshot[1][outside]['rain'] == 0
    assert snapshot[0][outside] is not None  # Old individual entries are ignored in circle scope.
    scenario.area.radius_m = 1000
    service.store.put('scenario', 'circle', scenario.model_dump())
    assert all(c['rain'] == 1 for c in service.snapshot('circle')[1].values())


@pytest.mark.parametrize('area', [None, {'lat': 23.77, 'lon': 90.4, 'radius_m': 0}, {'lat': 23.77, 'lon': 90.4, 'radius_m': 20001}])
def test_circle_requires_valid_area(area):
    with pytest.raises(ValidationError):
        Scenario(name='Invalid circle', scope='circle', area=area)
