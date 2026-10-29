from . import bfs, dfs, ids, ucs, astar
from .core import Limits

ALGORITHMS = {'BFS': bfs.run, 'DFS': dfs.run, 'IDS': ids.run, 'UCS': ucs.run, 'A*': astar.run}
