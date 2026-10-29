from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Conditions(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    traffic: float = Field(0, ge=0, le=1)
    condition: float = Field(0, ge=0, le=1)
    rain: float = Field(0, ge=0, le=1)
    safety: float = Field(0, ge=0, le=1)
    blocked: bool = False


class Weights(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    traffic: float = Field(2, ge=0, le=10)
    condition: float = Field(1, ge=0, le=10)
    rain: float = Field(2, ge=0, le=10)
    safety: float = Field(1, ge=0, le=10)


class Scenario(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    name: str = Field(min_length=1, max_length=80)
    description: str = Field('', max_length=500)
    road_classes: list[str] = Field(default_factory=list, max_length=30)
    conditions: Conditions = Field(default_factory=Conditions)
    edges: dict[str, Conditions] = Field(default_factory=dict, max_length=10000)
    weights: Weights = Field(default_factory=Weights)


class RouteQuery(BaseModel):
    model_config = ConfigDict(extra='forbid')
    start: str
    destination: str
    algorithm: Literal['BFS', 'DFS', 'IDS', 'UCS', 'A*', 'all'] = 'all'
    scenario: str = 'normal'
    max_expansions: int = Field(100000, ge=1, le=300000)
    max_depth: int = Field(100, ge=0, le=500)
    timeout_seconds: float = Field(3, ge=0.01, le=10, allow_inf_nan=False)
    trace_limit: int = Field(300, ge=0, le=2000)
    zero_heuristic_comparison: bool = True


class Point(BaseModel):
    lat: float = Field(ge=-90, le=90, allow_inf_nan=False)
    lon: float = Field(ge=-180, le=180, allow_inf_nan=False)
    max_distance_m: float = Field(500, gt=0, le=2000, allow_inf_nan=False)


class ScenarioComparison(BaseModel):
    query: RouteQuery
    scenarios: list[str] = Field(min_length=1, max_length=8)
