# Vanya Park Observation - Explore Enclave

## Hypothesis
`RUTE INTERMODA - VANYA PARK - INTERMODA` (orange, #F97316) exists as loop via overview image.

## Evidence

### Trace 1 (overview image 1, orange line, north segment)
- PASAR MODERN (HUB, bottom) -> Simplicity 1? -> ... -> GPS? Actually overview shows orange line starting at PASAR MODERN, going north along west side, then east via ??? Hard to distinguish due to overlapping yellow/red in same corridor.
- North segment appears to branch east near The Breeze / SML Plaza area, looping via "Vanya Park" cluster (not labeled in singular images, only in overview central south of THE BREEZE?).
- Label "VANYA PARK" visible near middle-right? Not in singular maps, inferred near `Griya Loka` area in overview? Check overview: orange line thickness distinct but halte dots obscured by other colors.

### Trace 2 (second independent trace, focusing on dashed vs solid)
- Overview orange appears solid northbound, dashed southbound? Similar to pink R2 dashed segment near The Breeze.
- Possible stops overlapping with YELLOW (INT-BREEZE-INT) corridor => contamination risk.

### Agreement
- Both traces agree origin/destination = PASAR MODERN loop, direction = LOOP.
- Both agree passes through `AEON` vs `ICON` corridor ambiguous - overlapping lines make AEON vs Vanya distinction low confidence.
- Sequence beyond PASAR MODERN -> Vanya Park -> back to PASAR MODERN not reconstructable at halt-level from overview alone.

## Decision (Deliver with Explore enclave)

- Ship `route_id=INT_VANYA_INT` with `is_inferred=true`, `stop_type` only for PASAR_MODERN (confirmed) + VANYA_PARK cluster inferred stops as `STOP_ID=VANYA_PARK_1` placeholder.
- `route_stops` rows for Vanya marked `is_inferred=true`, `notes=INFERRED_FROM_OVERVIEW_LOW_RES`.
- `trips.csv` / `stop_times.csv` left empty for Vanya (no timetable legible on overview). Don't invent times.
- Escalation: if future high-res singular Vanya map provided, replace inferred rows with measured seq and set `is_inferred=false`.

## Next
- Transcribe placeholder 3-stop loop for validator: PASAR_MODERN -> VANYA_PARK -> PASAR_MODERN (seq 1-3). Keeps FK valid, signals partial data.
- Document residual risk: distance/time not queryable for Vanya until high-res source.

## Timestamp
2026-05-13T00:00:00Z
