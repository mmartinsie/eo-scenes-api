"""Ports: what the core needs from the outside world, without saying how."""

from typing import Protocol

from eo_scenes_api.domain import Scene, SearchQuery


class SceneRepository(Protocol):
    async def add_many(self, scenes: list[Scene]) -> int: ...

    async def search(self, query: SearchQuery) -> list[Scene]: ...
