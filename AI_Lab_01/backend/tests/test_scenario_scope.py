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
    scenario = Scenario(name='Circle rain', scope='circle', area={'lat': 23.77, 'lon': 90.401, 'radius_m': 50}, conditions={'rain': 1}, edges={})
    service.store.put('scenario', 'circle', scenario.model_dump())
    snapshot = service.snapshot('circle')
    assert snapshot[1][crossing]['rain'] == 1  # Both endpoints are outside, but the line crosses the circle.
    assert snapshot[1][outside]['rain'] == 0
    assert snapshot[0][outside] is not None  # Outside the circle stays normal.
    scenario.area.radius_m = 1000
    service.store.put('scenario', 'circle', scenario.model_dump())
    assert all(c['rain'] == 1 for c in service.snapshot('circle')[1].values())


@pytest.mark.parametrize('area', [None, {'lat': 23.77, 'lon': 90.4, 'radius_m': 0}, {'lat': 23.77, 'lon': 90.4, 'radius_m': 20001}])
def test_circle_requires_valid_area(area):
    with pytest.raises(ValidationError):
        Scenario(name='Invalid circle', scope='circle', area=area)


def test_multiple_circles_union_without_double_penalty(tmp_path, graph):
    service = Service(tmp_path, graph)
    first = {'lat': 23.77, 'lon': 90.401, 'radius_m': 50}
    second = {'lat': 23.771, 'lon': 90.403, 'radius_m': 50}
    scenario = Scenario(name='Two rain areas', scope='circle', areas=[first, second, first], conditions={'rain': 1})
    service.store.put('scenario', 'multiple', scenario.model_dump())
    costs, conditions, *_ = service.snapshot('multiple')
    crossing = next(key for key, edge in service.edges.items() if edge == ('s', 'b', '0'))
    near_goal = next(key for key, edge in service.edges.items() if edge == ('b', 't', '0'))
    outside = next(key for key, edge in service.edges.items() if edge == ('a', 's', '0'))
    assert conditions[crossing]['rain'] == conditions[near_goal]['rain'] == 1
    assert costs[crossing] == pytest.approx(0.210 * 3)
    assert conditions[outside]['rain'] == 0
    # Removing the second circle restores its roads to baseline.
    scenario.areas = [scenario.areas[0]]
    service.store.put('scenario', 'multiple', scenario.model_dump())
    assert service.snapshot('multiple')[1][near_goal]['rain'] == 0


def test_rejects_more_than_twenty_circles():
    with pytest.raises(ValidationError):
        Scenario(name='Too many', scope='circle', areas=[{'lat': 23.77, 'lon': 90.4, 'radius_m': 500}] * 21)


def test_circles_have_independent_conditions_and_specific_roads_take_priority(tmp_path, graph):
    service = Service(tmp_path, graph)
    crossing = next(key for key, edge in service.edges.items() if edge == ('s', 'b', '0'))
    near_goal = next(key for key, edge in service.edges.items() if edge == ('b', 't', '0'))
    outside = next(key for key, edge in service.edges.items() if edge == ('a', 's', '0'))
    scenario = Scenario(name='Mixed weather', scope='circle', areas=[
        {'lat': 23.77, 'lon': 90.401, 'radius_m': 50, 'conditions': {'rain': 1}},
        {'lat': 23.771, 'lon': 90.403, 'radius_m': 50, 'conditions': {'traffic': 1}},
        {'lat': 23.77, 'lon': 90.401, 'radius_m': 50, 'conditions': {'traffic': 0.5, 'rain': 0.5}},
    ])
    service.store.put('scenario', 'mixed', scenario.model_dump())
    conditions = service.snapshot('mixed')[1]
    assert conditions[crossing]['rain'] == 1
    assert conditions[crossing]['traffic'] == 0.5
    assert conditions[near_goal]['rain'] == 0
    assert conditions[near_goal]['traffic'] == 1
    assert conditions[outside]['rain'] == conditions[outside]['traffic'] == 0
    scenario.edges[crossing] = scenario.conditions.model_copy(update={'blocked': True})
    service.store.put('scenario', 'mixed', scenario.model_dump())
    assert service.snapshot('mixed')[0][crossing] is None
    service.store.put('override', crossing, {'traffic': 0, 'condition': 0, 'rain': 0, 'safety': 0, 'blocked': False})
    assert service.snapshot('mixed')[0][crossing] is not None
