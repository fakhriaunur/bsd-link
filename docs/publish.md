# Publish - Split Dataset vs Scenarios (C2) + 404 Fix

Source truth `data/csv` -> derived `data/json` (gitignored) -> `dist/api` (dataset). Scenarios `scenarios/*.yaml` -> `dist/scenarios` via `route` pure core. Both deploy to same Pages site `https://<user>.github.io/bsd-link/` with `dist/index.html` landing + `.nojekyll`.

## Local

```bash
python scripts/build.py              # validate + derive data/json + data/geo
python scripts/publish.py            # build + copy to dist/api + index.json + dist/index.html + .nojekyll
python scripts/publish.py --check    # fail if dist/api stale vs csv>json>dist
python scripts/publish_scenarios.py  # snapshot dep: restores data/json from dist/api if missing, solves scenarios -> dist/scenarios/*.json + yaml copy + dist/scenarios/index.json, updates dist/index.html
python scripts/publish_scenarios.py --check
python scripts/publish_scenarios.py --dry-run
# preview both
python -m http.server --directory dist 8000
# open http://localhost:8000/ (landing) http://localhost:8000/api/index.json http://localhost:8000/scenarios/index.json
```

## CI - Split Workflows (separate GH Action paths, queued via same concurrency `group: pages`)

**Dataset:** `.github/workflows/publish-dataset.yml` triggers on `push:main` paths `data/csv/**`, `scripts/build.py`, `scripts/publish.py`, `.github/workflows/publish-dataset.yml` + `workflow_dispatch`:
1. `setup-python 3.11`, `pip install pytest pyyaml`, `build.py`, `build.py --check`, `pytest`, `publish.py`, `publish.py --check`, `upload-pages-artifact path: dist`, `deploy-pages`

**Scenarios:** `.github/workflows/publish-scenarios.yml` triggers on `push:main` paths `scenarios/**`, `scripts/route.py`, `scripts/bsd.py`, `scripts/publish_scenarios.py`, `.github/workflows/publish-scenarios.yml` + `workflow_dispatch`:
1. `setup-python`, `pip install pytest pyyaml`, `pytest`, `publish_scenarios.py` (no `build` - depends on dataset snapshot: if `data/json` missing, restores from committed `dist/api` snapshot), `publish_scenarios.py --check`, `ls -R dist`, `upload-pages-artifact path: dist`, `deploy-pages`
- No force dataset build without dataset changes: scenario workflow reuses `dist/api` committed snapshot, not `build.py`.

Both share `concurrency: group: pages, cancel-in-progress: false` -> queued sequential deploys, no overwrite race. Each builds full `dist` (`api/` + `scenarios/` + `index.html`) before upload.

No `data/json` committed; `dist` committed for local demo, Pages artifact from workflow. Force republish via `workflow_dispatch` or empty commit touching watched path.

## Endpoints

- `/api/routes.json` (9 routes, color, inferred flag)
- `/api/stops.json` (41 haltes, lat/lng web-verified 5 majors)
- `/api/route_stops.json` (95 ordered)
- `/api/trips.json` (108)
- `/api/stop_times.json` (1259 realistic deltas variance 3-4)
- `/api/halte_index.json` (34 stops -> routes)
- `/api/build_meta.json` (counts, generated_at)
- `/api/routes.geojson` (41 Points + 9 LineStrings)
- `/api/index.json` (manifest)
- `/scenarios/index.json` (3 scenarios manifest)
- `/scenarios/<name>.json` (solved route, e.g., `least-transfer` 95min 2 transfers) + `.yaml` copy
- `/index.html` (landing with links to `api` + `scenarios`, fixes Pages 404) + `.nojekyll`

## Cache

- Dataset: `--check` `csv > json > dist/api` chain
- Scenarios: `--check` `scenarios/*.yaml > dist/scenarios` plus snapshot `dist/api` exists check
- CI fails if stale, ensuring publish always fresh

## Rollback

Revert `data/csv` or `scenarios/*.yaml` commit, re-run respective `publish*.py` locally, push - Pages redeploys previous `dist`. No DB migration.

## Geo

`routes.geojson` now 41 Points + 9 LineStrings from `stops.csv lat,lng` (web-verified). `build.py` generates, `publish.py` copies to `dist/api/routes.geojson`.
