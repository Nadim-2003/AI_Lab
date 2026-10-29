import os
from pathlib import Path
from uuid import uuid4
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from shapely.geometry import box
from .models import Conditions, Scenario, RouteQuery, Point, ScenarioComparison
from .service import Service, BUILTINS


def create_app(data_dir=None, graph=None):
    service = Service(data_dir or os.environ.get('DATA_DIR', Path(__file__).resolve().parents[2] / 'data'), graph)
    app = FastAPI(title='Dhaka Route Lab', version='1.0.0', description='Directed OpenStreetMap routing with simulated conditions. Generalized cost is not time or distance.')
    app.state.service = service
    app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'], allow_methods=['*'], allow_headers=['*'])

    @app.exception_handler(RuntimeError)
    async def unavailable(request, exc):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=503, content={'detail': str(exc)})

    @app.exception_handler(ValueError)
    async def invalid(request, exc):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=422, content={'detail': str(exc)})

    @app.exception_handler(KeyError)
    async def missing(request, exc):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=404, content={'detail': str(exc).strip("'")})

    @app.get('/api/health')
    def health():
        return {'status': 'alive', 'dataset_ready': service.graph is not None}

    @app.get('/api/ready')
    def ready():
        service.ready()
        return service.stats()

    @app.get('/api/metadata')
    def metadata():
        return service.stats()

    @app.get('/api/places')
    def places(q: str = Query('', max_length=100), category: str = '', limit: int = Query(15, ge=1, le=100), west: float | None = None, south: float | None = None, east: float | None = None, north: float | None = None):
        service.ready()
        text = q.casefold().strip()
        found = [p for p in service.places if (not text or text in p['_search']) and (not category or p['category'] == category) and (west is None or west <= p['lon']) and (east is None or p['lon'] <= east) and (south is None or south <= p['lat']) and (north is None or p['lat'] <= north)]
        found.sort(key=lambda p: (not p['name'].casefold().startswith(text), p['name']))
        return [{k: v for k, v in p.items() if k != '_search'} for p in found[:limit]]

    @app.get('/api/places/{identifier:path}')
    def place(identifier: str):
        service.ready()
        result = next((p for p in service.places if p['id'] == identifier), None)
        if result is None:
            raise KeyError('Place not found')
        return {k: v for k, v in result.items() if k != '_search'}

    @app.post('/api/resolve')
    def resolve(point: Point):
        return service.snap(point.lat, point.lon, point.max_distance_m)

    @app.post('/api/routes')
    def routes(query: RouteQuery):
        return service.route(query)

    @app.post('/api/compare-scenarios')
    def compare(query: ScenarioComparison):
        with service.store.lock:
            snapshots = [(name, service.snapshot(name)) for name in query.scenarios]
        return [service.route(query.query.model_copy(update={'scenario': name}), snapshot) for name, snapshot in snapshots]

    @app.get('/api/scenarios')
    def scenarios():
        return [{'id': key, 'builtin': key in BUILTINS, **value} for key, value in service.scenarios().items()]

    def validate_scenario(value):
        service.ready()
        unknown = set(value.edges) - set(service.edges)
        if unknown:
            raise ValueError(f'Unknown directed edges: {sorted(unknown)[:5]}')

    @app.post('/api/scenarios', status_code=201)
    def create_scenario(value: Scenario):
        validate_scenario(value)
        identifier = str(uuid4())
        service.store.put('scenario', identifier, value.model_dump())
        return {'id': identifier, **value.model_dump()}

    @app.put('/api/scenarios/{identifier}')
    def update_scenario(identifier: str, value: Scenario):
        if identifier in BUILTINS:
            raise HTTPException(409, 'Duplicate a built-in scenario before editing it')
        with service.store.lock:
            if identifier not in service.scenarios():
                raise KeyError('Scenario not found')
            validate_scenario(value)
            service.store.put('scenario', identifier, value.model_dump())
        return {'id': identifier, **value.model_dump()}

    @app.delete('/api/scenarios/{identifier}')
    def delete_scenario(identifier: str):
        if identifier in BUILTINS:
            raise HTTPException(409, 'Built-in scenarios cannot be deleted')
        with service.store.lock:
            if identifier not in service.scenarios():
                raise KeyError('Scenario not found')
            service.store.delete('scenario', identifier)
        return {'deleted': identifier}

    @app.get('/api/roads')
    def roads(west: float = 90.30, south: float = 23.65, east: float = 90.50, north: float = 23.90, scenario: str = 'normal', road_class: str = '', limit: int = Query(2500, ge=1, le=5000)):
        service.ready()
        if not (-180 <= west <= east <= 180 and -90 <= south <= north <= 90):
            raise ValueError('Invalid geographic bounds')
        snapshot = service.snapshot(scenario)
        indices = service.road_index.query(box(west, south, east, north), predicate='intersects')
        identifiers = [service.edge_ids[int(i)] for i in indices]
        if road_class:
            identifiers = [i for i in identifiers if road_class in str(service.graph[service.edges[i][0]][service.edges[i][1]][service.edges[i][2]].get('highway', ''))]
        return {'type': 'FeatureCollection', 'features': [service.road(i, snapshot) for i in identifiers[:limit]], 'truncated': len(identifiers) > limit, 'matched': len(identifiers), 'snapshot': snapshot[4]}

    @app.get('/api/road')
    def road(id: str, scenario: str = 'normal'):
        return service.road(id, service.snapshot(scenario))

    @app.put('/api/overrides')
    def override(value: Conditions, id: str):
        service.ready()
        if id not in service.edges:
            raise KeyError('Road edge not found')
        service.store.put('override', id, value.model_dump())
        return {'saved': id, 'revision': service.store.revision()}

    @app.delete('/api/overrides')
    def reset(id: str | None = None):
        service.ready()
        if id is not None and id not in service.edges:
            raise KeyError('Road edge not found')
        service.store.delete('override', id)
        return {'reset': id or 'all', 'revision': service.store.revision()}

    return app


app = create_app()
