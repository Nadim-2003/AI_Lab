import networkx as nx
import pytest
from shapely.geometry import LineString


@pytest.fixture
def graph():
    graph = nx.MultiDiGraph(crs='EPSG:4326')
    for node, x, y in [('s', 90.4, 23.77), ('a', 90.401, 23.771), ('b', 90.402, 23.77), ('t', 90.403, 23.771), ('island', 90.42, 23.78)]:
        graph.add_node(node, x=x, y=y)
    graph.add_edge('s', 'a', key='expensive', length=500, highway='primary', osmid=1)
    graph.add_edge('s', 'a', key='curve', length=160, highway='primary', osmid=2, geometry=LineString([(90.4,23.77), (90.4004,23.7708), (90.401,23.771)]))
    graph.add_edge('a', 't', key='0', length=240, highway='residential', osmid=3)
    graph.add_edge('s', 'b', key='0', length=210, highway='service', osmid=4)
    graph.add_edge('b', 't', key='0', length=210, highway='service', osmid=5)
    graph.add_edge('a', 's', key='0', length=160, highway='primary', osmid=6)
    return graph
