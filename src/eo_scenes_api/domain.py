"""Domain model: what a scene is and what searching means. No frameworks here."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class BBox:
    west: float
    south: float
    east: float
    north: float

    def __post_init__(self) -> None:
        if not (-180 <= self.west <= 180):
            raise ValueError(f"west must be in [-180, 180], got {self.west}")
        if not (-180 <= self.east <= 180):
            raise ValueError(f"east must be in [-180, 180], got {self.east}")
        if not (-90 <= self.north <= 90):
            raise ValueError(f"north must be in [-90, 90], got {self.north}")
        if not (-90 <= self.south <= 90):
            raise ValueError(f"south must be in [-90, 90], got {self.south}") 
        if self.west > self.east:
            raise ValueError(f"west ({self.west}) must not be greater than east ({self.east})") 
        if self.south > self.north:
            raise ValueError(f"south ({self.south}) must not be greater than north ({self.north})")

    def intersects(self, other: "BBox") -> bool:
        if self.west <= other.east and other.west <= self.east:
            if self.south <= other.north and other.south <= self.north:
                return True
        return False


@dataclass(frozen=True)
class Scene:
    id: str
    collection: str
    acquired: datetime
    bbox: BBox
    cloud_cover: float | None


@dataclass(frozen=True)
class SearchQuery:
    bbox: BBox | None = None
    start: datetime | None = None
    end: datetime | None = None
    limit: int = 20

    def __post_init__(self) -> None:
        if self.limit not in range(1, 101):
            raise ValueError(f"limit must be in [1, 100], got {self.limit}") 
        if self.start is not None and self.start.tzinfo is None:
            raise ValueError(f"start must include a timezone, e.g. 2026-11-02T00:00:00Z, got {self.start}")
        if self.end is not None and self.end.tzinfo is None:
            raise ValueError(f"end must include a timezone, e.g. 2026-11-02T00:00:00Z, got {self.end}")
        if self.start is not None and self.end is not None:
            if self.start > self.end:
                raise ValueError(f"start ({self.start}) must not be greater than end ({self.end})")
