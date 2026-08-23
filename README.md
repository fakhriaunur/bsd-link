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

## Coverage

| Route | Stops | Trips | StopTimes | Source |
|-------|-------|-------|-----------|--------|
| INT_SEKT13 | 13 | 13 | ~169 | Image1 |
| ... | ... | ... | ... | ... |
| INT_VANYA_INT | ~10 inferred | 0 | 0 | overview low-res |

Vanya Park: orange line inferred from overview image, `is_inferred=true`, timetable not available - needs high-res singular image.

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
