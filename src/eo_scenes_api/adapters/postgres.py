"""PostgreSQL SceneRepository: SQLAlchemy 2.0 Core on asyncpg."""

from sqlalchemy import Column, DateTime, Float, MetaData, String, Table, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncEngine

from eo_scenes_api.domain import BBox, Scene, SearchQuery

metadata = MetaData()

scenes_table = Table(
    "scenes",
    metadata,
    Column("id", String, primary_key=True),
    Column("collection", String, nullable=False),
    Column("acquired", DateTime(timezone=True), nullable=False, index=True),
    Column("west", Float, nullable=False),
    Column("south", Float, nullable=False),
    Column("east", Float, nullable=False),
    Column("north", Float, nullable=False),
    Column("cloud_cover", Float),
)


class PostgresSceneRepository:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def add_many(self, scenes: list[Scene]) -> int:
        if not scenes:
            return 0
        rows = [
            {
                "id": scene.id,
                "collection": scene.collection,
                "acquired": scene.acquired,
                "west": scene.bbox.west,
                "south": scene.bbox.south,
                "east": scene.bbox.east,
                "north": scene.bbox.north,
                "cloud_cover": scene.cloud_cover,
            }
            for scene in scenes
        ]
        statement = insert(scenes_table).values(rows).on_conflict_do_nothing(index_elements=["id"])
        async with self._engine.begin() as connection:
            result = await connection.execute(statement)
            return result.rowcount

    async def search(self, query: SearchQuery) -> list[Scene]:
        statement = select(scenes_table)
        if query.bbox is not None:
            b = query.bbox
            statement = statement.where(
                scenes_table.c.west <= b.east,
                scenes_table.c.east >= b.west,
                scenes_table.c.south <= b.north,
                scenes_table.c.north >= b.south,
            )
        if query.start is not None:
            statement = statement.where(scenes_table.c.acquired >= query.start)
        if query.end is not None:
            statement = statement.where(scenes_table.c.acquired <= query.end)
        statement = statement.order_by(scenes_table.c.acquired.desc(), scenes_table.c.id.desc()).limit(query.limit)
        async with self._engine.connect() as connection:
            result = await connection.execute(statement)
            return [
                Scene(
                    id=row.id,
                    collection=row.collection,
                    acquired=row.acquired,
                    bbox=BBox(row.west, row.south, row.east, row.north),
                    cloud_cover=row.cloud_cover,
                )
                for row in result
            ]

