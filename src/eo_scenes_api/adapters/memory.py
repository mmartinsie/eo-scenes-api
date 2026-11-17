"""In-memory SceneRepository: used by the tests, behaves like the PostgreSQL adapter."""

from eo_scenes_api.domain import Scene, SearchQuery


class InMemorySceneRepository:
    def __init__(self) -> None:
        self._scenes: dict[str, Scene] = {}

    async def add_many(self, scenes: list[Scene]) -> int:
        count = 0
        for scene in scenes:
            if scene.id not in self._scenes:
                self._scenes[scene.id] = scene
                count += 1
        return count

    async def search(self, query: SearchQuery) -> list[Scene]:
        result = list(self._scenes.values())
        if query.bbox is not None:
            result = [s for s in result if s.bbox.intersects(query.bbox)]
        if query.start is not None:
            result = [s for s in result if s.acquired >= query.start]
        if query.end is not None:
            result = [s for s in result if s.acquired <= query.end]
        result = sorted(result, key=lambda s: (s.acquired, s.id), reverse=True)
        return result[: query.limit]
