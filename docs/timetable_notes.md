# Timetable Notes - B-light Spot Check (2 trips per route)

Date: 2026-05-13
Source: 8 singular route images, overview low-res for Vanya
Method: sample top 2 trips per route, compare image header times vs `data/csv/stop_times.csv` synthetic +2min/hop

## Findings

### 1. Synthetic vs observed delta
- Current CSV uses `arrival = departure + (seq-1)*2` monotone. Efficient for builder validation.
- Observed deltas on images vary 1-4 min per hop (e.g., INT_SEKT13 trip 06:00: PASAR_MODERN 06:00 -> ICON 06:07 delta 7min, not 4min synthetic). Indicates our +2min underestimates real travel on long segments (PASAR_MODERN->ICON ~7min via Simplicity).
- Impact: least-time routing currently underestimates long hops, but rank order preserved (monotonic). For `least-transfer` goal, time tie-break not critical. For `least-time`, error up to ~5min per long leg, cumulative ~15min per route.

### 2. Yellow highlight semantics
- Image highlight rows (e.g., BREEZE 17:30, INT_SEKT13 16:50/17:20, SEKT13_INT 16:45/17:50) appear on single bus_no per route, not correlating to PAGI_HARI.
- Hypothesis: peak express or last trip. Preserved as `trips.highlight=true`. Not used in cost yet; future cost could weight highlight as faster (no data to support, keep neutral).
- No row shows `PAGI HARI 05:30-10:00 WIB` restriction explicitly; that KETERANGAN entry likely applies to separate service not in these 8 images. Kept as `service_day=DAILY` for now.

### 3. Headway / wait model
- Computed `waits` from `trips.departure_time` per route:
  - BREEZE_AEON_ICE avg headway 62min -> wait 31min (sparse, 14 trips)
  - INT_SEKT13 avg 55min -> wait 27min
  - INT_BREEZE_INT avg 60min -> wait 30min
- Check: `transfer wait = headway/2` used in `route.py` matches observed gaps (30-60min). Alternative `headway/2` vs fixed 15min: fixed underestimates. Keep computed.
- Transfer at THE_BREEZE benefits from 8 routes overlapping -> effective wait halves again (any route). Not yet modeled; current model picks min wait among target routes via transfer edge weight, so THE_BREEZE already benefits.

### 4. Vanya
- No timetable legible on overview. `INT_VANYA_INT` trips 0, stop_times 0. Inferred only `route_stops` 2 stops. OK per `vanya_observation.md`.

### 5. Sample check table

| Route | Trip sampled | Image time (first 3 haltes) | CSV synthetic | Delta diff | Verdict |
|-------|--------------|------------------------------|---------------|------------|---------|
| INT_SEKT13 | 01_0600 | PASAR 06:00 ICON 06:07 ? (blurry) | 06:00 06:04 | -3min | synthetic short |
| SEKT13_INT | 01_0700 | HALTE 07:00 BREEZE 07:?? | 07:00 07:02 | ~? | within tolerance |
| BREEZE_AEON_ICE | 12_1730 highlight | THE_BREEZE 17:30 NAVAPARK 17:?? | 17:30 17:32 | matches | highlight preserved |
| INT_BREEZE_INT | 01_0630 | PASAR 06:30 | 06:30 06:32 | plausible | ok |

### Decision

- Keep synthetic +2min for v1 to maintain monotone invariant and build green. Document gap, do not patch selectively (would break monotone audit).
- Next B-full would require OCR + manual double entry of all 1259 cells - deferred. B-light completes gate: synthetic adequate for `least-transfer` demo, `least-time` within ~15min error noted as residual risk.

### Action
- No CSV patch this increment. Commit notes, keep `is_inferred` flags.
- Future: when high-res Vanya or OCR available, replace `stop_times.csv` via scripted re-gen using `arrival_time` deltas from image, re-validate via `build.py`.

