# BSD Link - Dataset

Source of truth: `data/csv/` (CSV). Derived: `data/json/` via `scripts/build.py`. Never hand-edit JSON.

## KETERANGAN (single legend)

| Color | Route |
|-------|-------|
| #1E40AF dark blue | RUTE INTERMODA - SEKTOR I.3 |
| #06B6D4 cyan | RUTE SEKTOR I.3 - INTERMODA |
| #166534 dark green | RUTE GREENWICH PARK - SEKTOR I.3 |
| #84CC16 lime | RUTE SEKTOR I.3 - GREENWICH PARK |
| #DC2626 red | RUTE INTERMODA - DEPARK (RUTE 1) |
| #EC4899 pink | RUTE INTERMODA - DEPARK (RUTE 2) |
| #9333EA purple | RUTE THE BREEZE - AEON - ICE - THE BREEZE |
| #EAB308 yellow | RUTE INTERMODA - THE BREEZE - INTERMODA |
| #F97316 orange | RUTE INTERMODA - VANYA PARK - INTERMODA (inferred) |

Halte types: `HALTE_BUS` ●, `BUS_STOP` ○, `PUTAR_BALIK` ⬢, `HUB`

## Quick start

```bash
python scripts/build.py              # validate + derive data/json
python scripts/build.py --check      # fail if JSON stale
```

## Coverage (validated `build_meta.json` 2026)

| Route | Stops | Trips | StopTimes | Source | Inferred |
|-------|-------|-------|-----------|--------|----------|
| INT_SEKT13 | 12 | 13 | 156 | Image1 | false |
| SEKT13_INT | 11 | 13 | 143 | Image2 | false |
| GRN_SEKT13 | 10 | 13 | 130 | Image3 | false |
| SEKT13_GRN | 10 | 13 | 130 | Image4 | false |
| INT_DEPARK_R1 | 12 | 14 | 168 | Image5 | false |
| INT_DEPARK_R2 | 13 | 14 | 182 | Image6 | false |
| BREEZE_AEON_ICE | 12 | 14 | 168 | Image7 | false |
| INT_BREEZE_INT | 13 | 14 | 182 | Image9 | false |
| INT_VANYA_INT | 2 | 0 | 0 | overview | true |
| **Total** | **95 route_stops** | **108** | **1259** | 41 deduped haltes, halte_index 34 | 1 route, 2 stops inferred |

Vanya Park: orange line inferred from overview image, `is_inferred=true`, timetable not available - needs high-res singular image. See `docs/vanya_observation.md`.

## Geo (now available)

- `stops.csv` now has `lat,lng` 41 BSD City coords (-6.321..-6.285,106.636..106.661)
- `scripts/build.py` generates `data/geo/routes.geojson` 41 Points + 9 LineStrings (per `route_stops` order)
- Publish includes `dist/api/routes.geojson` - view via `python -m http.server --directory dist 8000` then `http://localhost:8000/api/routes.geojson` or drag to geojson.io
- Schema `schema.md:3` updated, `docs/publish.md` covers `dist/api`

## Directory

```
data/csv/routes.csv
data/csv/stops.csv
data/csv/route_stops.csv
data/csv/trips.csv
data/csv/stop_times.csv
data/json/*.json (generated)
scripts/build.py
schema.md
docs/vanya_observation.md
```

## Query examples

- Halte -> routes: `jq '.["THE_BREEZE"]' data/json/halte_index.json`
- Route ordered stops: `data/json/route_stops.json | jq 'map(select(.route_id=="INT_SEKT13")) | sort_by(.seq)'`
- CLI: `python scripts/bsd.py --halte THE_BREEZE`
- Next departures: `python scripts/bsd.py --next PASAR_MODERN --time 07:00`
- Scenario: `python scripts/bsd.py --scenario scenarios/intermoda-aeon-breeze-icon-least-transfer.yaml`
- List: `python scripts/bsd.py --list-routes` / `--list-stops`
- Tests: `python -m pytest tests/test_route.py -v`

## Scenarios

- `scenarios/intermoda-aeon-breeze-icon-least-transfer.yaml` (least-transfer 2 transfers, 95min, chain counts inter-leg)
- `scenarios/intermoda-aeon-breeze-icon-least-time.yaml` (least-time)
- `scenarios/intermoda-aeon-breeze-icon-least-walk.yaml` (walk AEON<->BREEZE 8min, 42min 0 transfers)
- Engine `scripts/route.py` pure core, Dijkstra tuple cost, transfer wait headway/2, see `docs/b_full.md` B-full realistic deltas variance 3-4 (no uniform flag), `docs/timetable_notes.md` B-light spot check.

## Publish (C2)

- `python scripts/publish.py --dry-run` preview, `--check` stale, no args publish to `dist/api`
- `dist/api/index.json` manifest + 9 files, GH Pages workflow `.github/workflows/publish.yml`
- `python scripts/quality.py` per route delta stats (now all variance>0), `python -m pytest` 5 green
