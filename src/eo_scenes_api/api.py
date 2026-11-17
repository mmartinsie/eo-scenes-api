"""HTTP driving adapter: translates HTTP requests into domain queries and back."""

from datetime import datetime

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from eo_scenes_api.domain import BBox, Scene, SearchQuery
from eo_scenes_api.ports import SceneRepository


class SceneOut(BaseModel):
    id: str
    collection: str
    acquired: datetime
    bbox: tuple[float, float, float, float]
    cloud_cover: float | None

    @classmethod
    def from_domain(cls, scene: Scene) -> "SceneOut":
        return cls(
            id=scene.id,
            collection=scene.collection,
            acquired=scene.acquired,
            bbox=(scene.bbox.west, scene.bbox.south, scene.bbox.east, scene.bbox.north),
            cloud_cover=scene.cloud_cover,
        )


def parse_bbox(raw: str) -> BBox:
    parts = raw.split(",")
    if len(parts) != 4 :
        raise ValueError(f"bbox must be 4 comma-separated numbers (west,south,east,north), got {raw!r}")
    west, south, east, north = (float(p) for p in parts)
    return BBox(west, south, east, north)


def create_app(repository: SceneRepository, lifespan=None) -> FastAPI:
    app = FastAPI(title="EO Scenes API", lifespan=lifespan)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/scenes")
    async def search_scenes(
        bbox: str | None = Query(None, description="west,south,east,north"),
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 20,
    ) -> list[SceneOut]:
        try:
            query = SearchQuery(
                bbox=parse_bbox(bbox) if bbox is not None else None,
                start=start,
                end=end,
                limit=limit,
                )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        scenes = await repository.search(query)
        return [SceneOut.from_domain(scene) for scene in scenes]

    return app
