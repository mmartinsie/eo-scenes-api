# eo-scenes-api

REST API for Sentinel-2 scene metadata: search scenes by bounding box and
acquisition date. Built with FastAPI, PostgreSQL and a ports-and-adapters
architecture.

## Decisions

### The domain is plain frozen dataclasses, not Pydantic

- **Choice:** `BBox`, `Scene` and `SearchQuery` are `@dataclass(frozen=True)`
  with their rules checked in `__post_init__`. Pydantic is used only at the HTTP
  edge.
- **Alternative:** Pydantic models everywhere.
- **Why not:** the core stays free of frameworks. Validation in the domain
  applies to every entry point (HTTP, the seed script, a future harvester), not
  only to HTTP requests. `frozen` keeps an object valid after construction.

### Boxes that touch on an edge intersect

- **Choice:** intervals are closed (`<=`), so two boxes sharing only an edge
  intersect.
- **Alternative:** open intervals (`<`).
- **Why not:** a scene whose edge lies on the search edge does cover that line.
  It is also the convention of PostGIS `ST_Intersects`.

### Boxes crossing the antimeridian are out of scope (assumption)

- **Choice:** a bbox requires `west <= east`. A request with `west > east` gets
  a 400.
- **Alternative:** read `west > east` as a box that crosses longitude 180, as
  GeoJSON (RFC 7946) allows.
- **Why not:** it doubles the intersection logic (one box becomes two), and the
  target region (Europe) never crosses the antimeridian.

### Datetimes without a timezone are rejected

- **Choice:** `start` and `end` must include a timezone (e.g.
  `2026-11-02T00:00:00Z`). Without one, the API answers 400.
- **Alternative:** assume UTC when the timezone is missing.
- **Why not:** guessing hides client mistakes. Without the check, comparing a
  naive datetime with the timezone-aware `acquired` raises `TypeError`, which
  would be a 500.

### Ports are `typing.Protocol`, not abstract base classes

- **Choice:** `SceneRepository` is a `Protocol`. Adapters implement its methods
  without inheriting from it or importing it.
- **Alternative:** an `abc.ABC` with `@abstractmethod`.
- **Why not:** an ABC forces every adapter to inherit from a class in the core.
  With a `Protocol` they are fully decoupled (structural typing). Trade-off:
  conformance is checked by a static type checker, not at runtime. The project
  does not run one yet, so today the tests are what check the adapters; adding
  pyright to CI is the next step.

### Date filters are inclusive

- **Choice:** a scene matches when `start <= acquired <= end`. The in-memory and
  PostgreSQL adapters use the same operators.
- **Alternative:** a half-open interval, `start <= acquired < end`.
- **Why not:** "from 1 to 3 November" includes scenes taken exactly at either
  bound, which is what a user expects. Trade-off: with consecutive windows that
  share a bound, a scene exactly on it appears in both.
