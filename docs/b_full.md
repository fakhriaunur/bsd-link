# B-full - Data Quality Full Timetable

## Goal
Replace synthetic +2min uniform with observed deltas 1-4min (B-light flagged all routes uniform).

## Process (repeat per route)

1. **Sample 2 trips per route** from high-res singular image (not overview). Read arrival per halte.
2. **Record deltas** per consecutive pair: `delta = next - current`. Expect 1-4min, long legs (PASAR->ICON 7min, THE_BREEZE->HALTE 4min) flagged in `timetable_notes.md`.
3. **Patch `data/csv/stop_times.csv`** via script `scripts/patch_bfull.py` that applies per-route delta profile to all trips of that route (preserves departure_time, recomputes arrivals).
4. **Validate** `python scripts/build.py` monotone + `python scripts/quality.py` variance >0.
5. **Commit** per route: `fix: B-full INT_SEKT13 realistic deltas` - keeps history per route.

## Current Sample Correction (B-full demo)

Patched `INT_SEKT13` only as demonstration:
- Deltas: PASAR 0, SIMPLICITY +3, ICON +4 (total 7 PASAR->ICON), CBD +2, NAVAPARK +2, BREEZE +3, HALTE +4, GREEN +1, EKA1 +2, EKA2 +1, ICE1 +5, ICE2 +1
- Before: all 2min uniform, avg 2.0 variance 0
- After: avg 2.5, variance 4 (1-5 range), matches observed 1-4 + long legs

Other routes remain synthetic uniform - flagged in `quality.py`. Full B-full requires repeating patch per route when high-res images available.

## How to run B-full for a route

```bash
python scripts/patch_bfull.py --route INT_SEKT13 --profile realistic
python scripts/build.py
python scripts/quality.py  # should show variance >0 for that route
python scripts/publish.py --dry-run
```

Profile `realistic` defined in `scripts/patch_bfull.py` per route. Add new profiles as needed.

## Residual

- INT_VANYA_INT still 0 trips (needs singular image)
- Other 7 routes uniform - see `quality.py` flags. Publish with note `synthetic` in `build_meta.json` if needed.

## Next

- When high-res image for Vanya provided, run same process, clear `is_inferred` for route_stops and add trips.
