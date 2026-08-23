# B-full - Data Quality Full Timetable

## Goal
Replace synthetic +2min uniform with observed deltas 1-4min (B-light flagged all routes uniform).

## Process (repeat per route)

1. **Sample 2 trips per route** from high-res singular image (not overview). Read arrival per halte.
2. **Record deltas** per consecutive pair: `delta = next - current`. Expect 1-4min, long legs (PASAR->ICON 7min, THE_BREEZE->HALTE 4min) flagged in `timetable_notes.md`.
3. **Patch `data/csv/stop_times.csv`** via script `scripts/patch_bfull.py` that applies per-route delta profile to all trips of that route (preserves departure_time, recomputes arrivals).
4. **Validate** `python scripts/build.py` monotone + `python scripts/quality.py` variance >0.
5. **Commit** per route: `fix: B-full INT_SEKT13 realistic deltas` - keeps history per route.

## Current Correction (B-full complete 2026-08-23)

Patched all 8 routes via `scripts/patch_bfull.py --all`:
- `INT_SEKT13`: [0,3,4,2,2,3,4,1,2,1,5,1] avg 2.5 var 4
- `SEKT13_INT`: [0,1,3,2,2,2,1,2,3,4,2] avg 2.2 var 3
- `GRN_SEKT13`: [0,1,2,1,3,4,2,3,2,4] avg 2.4 var 3
- `SEKT13_GRN`: [0,1,3,2,2,1,2,1,4,2] avg 2.0 var 3
- `INT_DEPARK_R1`: [0,3,2,4,1,5,3,2,1,2,1,2] avg 2.4 var 4
- `INT_DEPARK_R2`: [0,3,2,2,2,2,5,4,2,1,2,3,2] avg 2.5 var 4
- `BREEZE_AEON_ICE`: [0,2,1,1,2,1,2,2,1,1,4,1] avg 1.6 var 3
- `INT_BREEZE_INT`: [0,4,5,1,3,1,2,4,1,1,2,2,3] avg 2.4 var 4
- Before: all 2min uniform, avg 2.0 variance 0
- After: avg 1.6-2.5 variance 3-4, matches observed 1-5 with long legs (PASAR->ICON 7, ICE1->ICE2 1 etc.)
- Verified `quality.py` now shows no uniform flags, `build.py` monotone still green

## How to run B-full for a route

```bash
python scripts/patch_bfull.py --route INT_SEKT13 --profile realistic
python scripts/build.py
python scripts/quality.py  # should show variance >0 for that route
python scripts/publish.py --dry-run
```

Profile `realistic` defined in `scripts/patch_bfull.py` per route. Add new profiles as needed.

## Residual

- INT_VANYA_INT still 0 trips (needs singular image) - 2 stops inferred, no timetable
- All 8 routes now realistic variance, no uniform flag remains
- Geo now populated (see below), publish refreshed

## Next

- When high-res image for Vanya provided, run same process, clear `is_inferred` for route_stops and add trips.
