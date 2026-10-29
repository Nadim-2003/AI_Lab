import networkx as nx
import pytest
from backend.app.algorithms import ALGORITHMS, Limits
from backend.app.geo import edge_geometry, route_geometry


def cost(u, v, k, attrs):
    return attrs['length'] / 1000


@pytest.mark.parametrize('name', ALGORITHMS)
def test_search_basic(graph, name):
    result = ALGORITHMS[name](graph, 's', 't', cost, Limits())
    assert result['found']
    assert result['nodes'][0] == 's' and result['nodes'][-1] == 't'
    for u, v, k in result['edges']:
        assert graph.has_edge(u, v, k)
    assert result['expanded'] > 0
    assert result['generated'] >= 3
    assert result['execution_ms'] >= 0


@pytest.mark.parametrize('name', ALGORITHMS)
def test_no_route_and_identity(graph, name):
    run = ALGORITHMS[name]
    assert run(graph, 't', 's', cost, Limits())['status'] == 'unreachable'
    assert not run(graph, 's', 'island', cost, Limits())['found']
    identity = run(graph, 's', 's', cost, Limits())
    assert identity['found'] and identity['edges'] == [] and identity['cost'] == 0


@pytest.mark.parametrize('name', ['UCS', 'A*'])
def test_weighted_parallel_edge_selection(graph, name):
    result = ALGORITHMS[name](graph, 's', 't', cost, Limits())
    assert result['edges'] == [['s', 'a', 'curve'], ['a', 't', '0']]
    assert result['cost'] == pytest.approx(.4)
    geometry = route_geometry(graph, result['edges'])
    assert geometry['coordinates'][1] == [90.4004, 23.7708]
    assert len(geometry['coordinates']) == 4


@pytest.mark.parametrize('name', ALGORITHMS)
def test_blocking_and_limits(graph, name):
    blocked = lambda u, v, k, attrs: None if v == 't' else cost(u, v, k, attrs)
    assert not ALGORITHMS[name](graph, 's', 't', blocked, Limits())['found']
    result = ALGORITHMS[name](graph, 's', 't', cost, Limits(max_expansions=1))
    assert result['status'] == 'expansion_limit'
    traced = ALGORITHMS[name](graph, 's', 't', cost, Limits(trace_limit=1))
    assert len(traced['trace']) <= 1


@pytest.mark.parametrize('name', ALGORITHMS)
def test_negative_cost_rejected(graph, name):
    with pytest.raises(ValueError, match='nonnegative'):
        ALGORITHMS[name](graph, 's', 't', lambda *args: -1, Limits())


def test_depth_and_bfs_hops(graph):
    graph.add_edge('s', 't', key='direct', length=10000)
    assert ALGORITHMS['BFS'](graph, 's', 't', cost, Limits())['edges'] == [['s', 't', 'direct']]
    for name in ['DFS', 'IDS']:
        assert ALGORITHMS[name](graph, 's', 't', cost, Limits(max_depth=0))['status'] == 'depth_limit'


def test_missing_reversed_geometry_and_invalid(graph):
    assert edge_geometry(graph, 'a', 't', '0') == [[90.401, 23.771], [90.403, 23.771]]
    graph['a']['s']['0']['geometry'] = graph['s']['a']['curve']['geometry']
    assert edge_geometry(graph, 'a', 's', '0')[0] == [90.401, 23.771]
    graph['s']['a']['curve']['geometry'] = 'LINESTRING (181 23, 90 24)'
    with pytest.raises(ValueError, match='Invalid road'):
        edge_geometry(graph, 's', 'a', 'curve')


def test_invalid_nodes(graph):
    with pytest.raises(ValueError, match='exist'):
        ALGORITHMS['UCS'](graph, 'missing', 't', cost, Limits())
