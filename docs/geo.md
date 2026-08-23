# Geo - Cross-checked with Web

## Web sources (2026-08-23)

| Stop | Web lat,lng | Source | Previous synthetic | Delta | Action |
|------|-------------|--------|-------------------|-------|--------|
| PASAR_MODERN | -6.3045281,106.6848223 | maptons.com / flokq -6.30442599,106.6851166 | -6.3215,106.6462 | 1.9km S, 4.2km W | **corrected** to -6.30453,106.68482 |
| ICE BSD (ICE_1) | -6.300258,106.636604 | en.wikipedia ICE | -6.2985,106.6365 | 200m N | corrected to -6.300258,106.636604 |
| THE_BREEZE | -6.302222,106.65445 (also -6.3031449,106.6541336) | exploresunda / occupi | -6.3035,106.6525 | 300m E | corrected to -6.30222,106.65445 |
| AEON_MALL BSD | -6.3045,106.643 (getamap) / -6.302778,106.636383 | getamap / exploresunda | -6.3025,106.6505 | 800m E | corrected to -6.3045,106.643 |
| Q_BIG BSD | -6.286535,106.636791 | exploresunda | -6.2875,106.6455 | 900m E | corrected to -6.286535,106.636791 |
| BSD City center | -6.30056,106.65222 | en.wikipedia BSD City | — | — | reference |

## Impact

- PASAR_MODERN synthetic was off by ~4km (Intermoda hub is east near Serpong, not south). Corrected anchor shifts all southern corridor stops (SIMPLICITY, ELDORADO, ICON) now correctly 1-2km west of Pasar, not south.
- ICE and THE_BREEZE were already within 300m, minor tweak.
- AEON now correctly west of THE_BREEZE, near ICE, matches BSD Link shuttle `THE BREEZE - AEON - ICE` loop topology (previously AEON was east of Breeze, reversed).
- Q_BIG now north correctly.

## Remaining 21 stops

Synthetic coords remain plausible within BSD bounds -6.285..-6.321,106.636..106.661, interpolated relative to corrected anchors. No web source for halte-level stops (e.g., FBL_1, CBD Barat) - kept as relative offsets from nearest anchor (e.g., CBD Barat near AEON/THE_BREEZE). Future refinement can use OSM Overpass `highway=bus_stop` in BSD City bbox.

## Output

- `data/csv/stops.csv` now 41 rows with `lat,lng` web-verified for 5 majors + 15 nearby adjusted, total 20 corrected.
- `data/geo/routes.geojson` 41 Points + 9 LineStrings, validated `build.py` generates `LineString` per `route_stops` order.
- `dist/api/routes.geojson` published via `publish.py` -> `dist/api` + Pages workflow.

## How to verify

```bash
python scripts/build.py
python -c "import json; g=json.load(open('data/geo/routes.geojson')); print(len([f for f in g['features'] if f['geometry']['type']=='Point']))"
# compare with web: https://www.google.com/maps/search/?api=1&query=-6.304528,106.684822
```
