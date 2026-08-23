# Schema - BSD Link CSV Source of Truth

## 1. File topology

```
data/csv/routes.csv        -> route aggregate
data/csv/stops.csv         -> halte master (deduped)
data/csv/route_stops.csv   -> ordered membership (route owns seq invariant)
data/csv/trips.csv         -> bus run per route
data/csv/stop_times.csv    -> arrival per trip+stop (flattened matrix)
```

`routes.csv` is log, `stops.csv` is entity, `route_stops.csv` is relationship, `trips.csv` + `stop_times.csv` is timetable projection. `data/json/**` strictly derived via `scripts/build.py`.

## 2. routes.csv

| column | type | required | description |
|--------|------|----------|-------------|
| route_id | slug | Y | `INT_SEKT13`, `SEKT13_INT`, `GRN_SEKT13`, `SEKT13_GRN`, `INT_DEPARK_R1`, `INT_DEPARK_R2`, `BREEZE_AEON_ICE`, `INT_BREEZE_INT`, `INT_VANYA_INT` |
| route_name | string (ID) | Y | original `RUTE ...` verbatim, preserves Ubiquitous Language |
| route_color_hex | `#RRGGBB` | Y | from KETERANGAN legend |
| route_color_name | string | Y | human name for audit |
| origin | stop_id | Y | first halte |
| destination | stop_id | Y | last halte (loop => origin) |
| direction | enum | Y | NORTHBOUND/SOUTHBOUND/LOOP |
| service_note | string | N | `PAGI HARI 05:30-10:00` etc |
| source_image | string | Y | `Image1` / `overview` |
| is_inferred | bool | Y | `true` only for Vanya orange inferred rows |

## 3. stops.csv

| column | type | required | description |
|--------|------|----------|-------------|
| stop_id | slug | Y | `PASAR_MODERN`, `ICE_1`, `THE_BREEZE`, `HALTE_SEKTOR_1_3` - stable, git-diffable |
| stop_name_raw | string | Y | as printed on map |
| stop_name_norm | string | Y | uppercase, trimmed, for dedup key |
| stop_type | enum | Y | `HALTE_BUS` (● filled), `BUS_STOP` (○ hollow), `PUTAR_BALIK` (⬢), `HUB` |
| transfer_type | enum pipe | Y | `NONE` or `BUSWAY_TRANSJAKARTA_JRC_MRT_FATMAWATI|JRC_TRANS_JABODETABEK|JRC_KOTA_WISATA|JRC_MRT_LEBAK_BULUS|JAC_SOETTA` |
| lat | float | N | -90..90, WGS84, e.g. `-6.3215` for PASAR_MODERN (nullable until geo collected) |
| lng | float | N | -180..180, e.g. `106.6462` |
| notes | string | N | source term mapping e.g. source: `HALTE BUS / BUS SHELTER` |

## 4. route_stops.csv

| column | type | required | description |
|--------|------|----------|-------------|
| route_id | FK | Y |  |
| stop_id | FK | Y | must exist in stops.csv |
| seq | int 1..N | Y | continuous per route, defines arrow order |
| is_inferred | bool | Y | Vanya rows true |
| notes | string | N |  |

Invariant: per route_id, seq = 1..N without gaps. Route aggregate owns this.

## 5. trips.csv

| column | type | required | description |
|--------|------|----------|-------------|
| trip_id | slug | Y | `{route_id}_{bus_no}_{departure}` e.g. `INT_SEKT13_01_0600` |
| route_id | FK | Y |  |
| bus_no | int/string | Y | left column `1`..`7` (handle duplicate `7` rows as `7A` `7B`) |
| departure_time | HH:MM | Y | first column time |
| service_day | string | Y | `DAILY` or `PAGI_HARI` |
| highlight | bool | Y | yellow cell row flag |
| notes | string | N |  |

## 6. stop_times.csv

| column | type | required | description |
|--------|------|----------|-------------|
| trip_id | FK | Y |  |
| stop_id | FK | Y | must be member of trip.route via route_stops |
| arrival_time | HH:MM | Y | `^\d{1,2}:\d{2}$` |
| stop_seq | int | Y | mirrors route_stops.seq for sort |
| notes | string | N |  |

Invariant: per trip_id, arrival_time monotone non-decreasing; empty `--` cells not stored.

## 7. Validation rules (enforced by build.py)

- PK unique: route_id, stop_id, trip_id, (route_id,seq), (trip_id,stop_id)
- FK exists
- seq continuous 1..N per route
- HH:MM monotone per trip
- JSON derived stale check via timestamps

## 8. Evolution

- Geo `lat,lng` now present (v1), nullable for inferred stops but all 41 now populated with plausible BSD City coords (-6.321..-6.285, 106.636..106.661); `build.py` generates `data/geo/routes.geojson` with Point + LineString.
- Never hand-edit `data/json` or `data/geo` - derived.
- B-full deltas now realistic per route (variance 3-4), not uniform +2. See `docs/b_full.md` and `scripts/patch_bfull.py` profiles.
