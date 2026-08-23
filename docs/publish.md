# Publish - Static JSON API (C2)

Source truth `data/csv` -> derived `data/json` (gitignored) -> `dist/api` (publish artifact).

## Local

```bash
python scripts/build.py              # validate + derive
python scripts/publish.py            # build + copy to dist/api + index.json
python scripts/publish.py --check    # fail if dist stale
python scripts/publish.py --dry-run  # preview without write
# preview
python -m http.server --directory dist 8000
# open http://localhost:8000/api/index.json
```

## CI (GitHub Pages)

Workflow `.github/workflows/publish.yml` triggers on push to `main` when `data/csv/**` changes:
1. `setup-python`, `build.py`, `build.py --check`, `pytest`
2. `publish.py` -> `dist/api`
3. `upload-pages-artifact` + `deploy-pages` -> `https://<user>.github.io/bsd-link/api/`

No `data/json` committed to `main`; `dist` is artifact only (not committed). For local C2 demo, `dist/api` is committed or served via `gh-pages` branch.

## Endpoints

- `/api/routes.json` (9 routes, color, inferred flag)
- `/api/stops.json` (41 haltes)
- `/api/route_stops.json` (95 ordered)
- `/api/trips.json` (108)
- `/api/stop_times.json` (1259)
- `/api/halte_index.json` (34 stops -> routes)
- `/api/build_meta.json` (counts, generated_at)
- `/api/routes.geojson` (stub, geo deferred)
- `/api/index.json` (manifest, usage)

## Cache

`--check` uses mtime: `csv > json > dist` chain. CI fails if stale, ensuring publish always fresh.

## Rollback

Revert `data/csv` commit, re-run `publish.py` locally, push - `gh-pages` redeploys previous `dist`. No DB migration.

## Geo deferred

`routes.geojson` stub empty FeatureCollection. When `stops.csv` gets `lat,lng`, `build.py` will populate, `publish.py` will include without workflow change.
