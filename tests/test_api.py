import asyncio
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from eo_scenes_api.adapters.memory import InMemorySceneRepository
from eo_scenes_api.api import create_app
from eo_scenes_api.domain import BBox, Scene

MADRID = Scene("madrid-1", "s2", datetime(2026, 11, 1, tzinfo=UTC), BBox(-4, 40, -3, 41), 10.0)
VALENCIA = Scene("valencia-1", "s2", datetime(2026, 11, 3, tzinfo=UTC), BBox(-0.8, 39, 0.2, 40), 3.0)


@pytest.fixture
def client() -> TestClient:
    repository = InMemorySceneRepository()
    asyncio.run(repository.add_many([MADRID, VALENCIA]))
    return TestClient(create_app(repository))


def test_without_filters_returns_newest_first(client: TestClient) -> None:
    response = client.get("/scenes")
    assert response.status_code == 200
    assert [s["id"] for s in response.json()] == ["valencia-1", "madrid-1"]


def test_bbox_keeps_only_intersecting_scenes(client: TestClient) -> None:
    response = client.get("/scenes", params={"bbox": "-3.8,40.3,-3.5,40.6"})
    assert [s["id"] for s in response.json()] == ["madrid-1"]


def test_start_keeps_only_newer_scenes(client: TestClient) -> None:
    response = client.get("/scenes", params={"start": "2026-11-02T00:00:00Z"})
    assert response.status_code == 200
    assert [s["id"] for s in response.json()] == ["valencia-1"]


@pytest.mark.parametrize("bad_bbox", ["1,2,3", "10,0,5,1", "-200,0,0,1", "a,b,c,d"])
def test_invalid_bbox_returns_400(client: TestClient, bad_bbox: str) -> None:
    response = client.get("/scenes", params={"bbox": bad_bbox})
    assert response.status_code == 400
