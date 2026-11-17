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

### The app is built by a factory that receives the repository

- **Choice:** `create_app(repository)` defines the routes inside the function,
  so they use the repository they were given. Tests pass the in-memory adapter;
  `main.py` passes the PostgreSQL one.
- **Alternative:** FastAPI `Depends` with a provider function, replaced in tests
  through `app.dependency_overrides`.
- **Why not:** the provider needs module-level state and tests need an override
  mechanism. With the factory the dependency is explicit and each test builds
  its own app.

### Invalid input: 400 for domain rules, 422 for types (temporary)

- **Choice:** a value that breaks a domain rule (`limit=0`, `bbox=10,0,5,1`)
  gets 400 with the domain's message. A value of the wrong type
  (`limit=abc`) gets FastAPI's default 422.
- **Alternative:** one status code and one error format for both.
- **Why not yet:** it is planned with RFC 9457 problem details (Day 2).

### SQLAlchemy Core, not the ORM

- **Choice:** the table is described with `Table` and `Column`, queries are
  built with `select` and `insert`, and the adapter maps rows to the domain
  dataclasses by hand.
- **Alternative:** the SQLAlchemy ORM, with mapped classes and a `Session`.
- **Why not:** the domain already has its own dataclasses. The ORM would add a
  second model of a scene and a unit of work that two queries do not need. Core
  keeps the SQL visible.

### A bbox is four float columns, not PostGIS

- **Choice:** `west`, `south`, `east` and `north` are `FLOAT` columns. The
  intersection is four comparisons in the `WHERE`, the same rule as
  `BBox.intersects`.
- **Alternative:** a PostGIS geometry column with `ST_Intersects` and a GiST
  index.
- **Why not:** for axis-aligned boxes, comparing numbers is enough, and PostGIS
  has to be enabled separately on Azure Database for PostgreSQL. Trade-off:
  there is no spatial index. If real scene footprints (polygons) were needed,
  PostGIS would be the next step.

### Inserts are idempotent

- **Choice:** `INSERT ... ON CONFLICT (id) DO NOTHING`. `add_many` returns how
  many rows were actually inserted, so inserting the same batch twice returns 0
  the second time.
- **Alternatives:** a plain `INSERT` that fails on duplicates, or an upsert
  (`ON CONFLICT DO UPDATE`).
- **Why not:** harvesting the same items twice must be harmless, not an error.
  A stored scene is treated as immutable. If the source starts correcting
  metadata for existing ids, an upsert is the change to make.

### Scene ids use the "C" collation

- **Choice:** the `id` column is `COLLATE "C"`: ids are compared byte by byte.
- **Alternative:** the database default (`en_US.utf8` in the Docker image).
- **Why not:** the default sorts like a dictionary and ignores punctuation and
  case on the first pass. Python compares code points. Scenes with the same
  `acquired` were therefore ordered differently by PostgreSQL and by the
  in-memory adapter. A parity check that runs the same queries against both
  adapters found it. With "C" they agree, comparisons are cheaper, and the
  order is predictable for keyset pagination.
