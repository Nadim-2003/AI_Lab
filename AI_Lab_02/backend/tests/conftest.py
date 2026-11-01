import pytest
from backend.app.models import Scenario, Road, Incident, Requirement, Resource, Hospital


@pytest.fixture
def small():
    return Scenario(
        nodes={"a": (90.39, 23.73), "b": (90.40, 23.73), "c": (90.41, 23.73)},
        roads=[
            Road(id="ab", u="a", v="b", distance_km=1, speed_kph=30),
            Road(id="bc", u="b", v="c", distance_km=1, speed_kph=30),
            Road(id="ac", u="a", v="c", distance_km=4, speed_kph=30),
            Road(id="ca", u="c", v="a", distance_km=2, speed_kph=30),
        ],
        resources=[
            Resource(
                id="R1",
                role="ambulance",
                station="S1",
                node="a",
                home_node="a",
                capabilities=["medical"],
                capacity=2,
            ),
            Resource(
                id="R2",
                role="ambulance",
                station="S2",
                node="c",
                home_node="c",
                capabilities=["medical"],
                capacity=2,
            ),
        ],
        hospitals=[Hospital(id="H", name="Test", node="c", beds=4)],
        incidents=[
            Incident(
                id="A",
                category="medical",
                node="b",
                requirements=[
                    Requirement(role="ambulance", patients=1, capabilities=["medical"])
                ],
            ),
            Incident(
                id="B",
                category="medical",
                node="c",
                requirements=[
                    Requirement(role="ambulance", patients=1, capabilities=["medical"])
                ],
            ),
        ],
        budget=10000,
    )
