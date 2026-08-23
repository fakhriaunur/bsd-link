# AGENTS.md — BSD Link

Source of truth: `data/csv/` (CSV). Derived: `data/json/` via `scripts/build.py`. Never hand-edit JSON. `data/geo/routes.geojson` derived from `stops.csv` lat/lng + `route_stops` order.

## Quick start

```bash
python scripts/build.py              # validate + derive data/json + data/geo
python scripts/build.py --check      # fail if JSON stale vs CSV
python -m pytest tests/test_route.py -q  # 5 tests (halte_index, graph, scenarios, monotone)
python scripts/bsd.py --halte THE_BREEZE
python scripts/bsd.py --next PASAR_MODERN --time 07:00
python scripts/bsd.py --scenario scenarios/intermoda-aeon-breeze-icon-least-transfer.yaml
python scripts/publish.py --dry-run  # preview dist/api
python scripts/publish.py --check    # fail if dist stale
python -m http.server --directory dist 8000  # http://localhost:8000/api/index.json
```

## Project structure

- `data/csv/routes.csv` — route aggregate (9 routes, color, inferred flag)
- `data/csv/stops.csv` — halte master (41 deduped, lat/lng)
- `data/csv/route_stops.csv` — ordered membership (95, seq 1..N per route)
- `data/csv/trips.csv` + `stop_times.csv` — timetable (108 trips, 1259 arrivals, monotone per trip)
- `scripts/build.py` — deep module, enforces PK/FK/seq/HH:MM invariants
- `scripts/route.py` — pure core Dijkstra tuple cost (least-transfer/time/walk)
- `scripts/bsd.py` — thin CLI shell over `route.py`
- `scripts/publish.py` + `publish_scenarios.py` — derive `dist/api` + `dist/scenarios` + `dist/index.html`
- `schema.md` — CSV topology + validation rules
- `docs/` — `b_full.md`, `geo.md`, `publish.md`, `timetable_notes.md`

## Conventions

- `stop_id` slug uppercase (`PASAR_MODERN`), `route_id` slug (`INT_SEKT13`)
- `HH:MM` monotone per `trip_id` by `stop_seq`
- `is_inferred=true` only for Vanya orange (needs high-res image)
- Commits: `feat:`, `fix:`, `docs:` prefix

## Quality

```bash
ruff check scripts/ tests/
black --check .
mypy --strict scripts/
pre-commit run --all-files
```

See `pyproject.toml` for `ruff`/`black`/`mypy`/`pytest` config.
