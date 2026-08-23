#!/usr/bin/env python3
"""
BSD Link builder - deep module hiding CSV complexity.

Usage:
  python scripts/build.py              # validate + write data/json
  python scripts/build.py --check      # exit non-zero if JSON stale vs CSV

Invariants enforced:
  - PK unique per file
  - FK exists (route_id, stop_id, trip_id)
  - route_stops.seq continuous 1..N per route
  - stop_times arrival HH:MM monotone per trip
"""
from __future__ import annotations
import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_DIR = ROOT / "data" / "csv"
JSON_DIR = ROOT / "data" / "json"
GEO_DIR = ROOT / "data" / "geo"

TIME_RE = re.compile(r"^\d{1,2}:\d{2}$")

class ValidationError(Exception):
    pass

def parse_bool(v: str) -> bool:
    if v is None:
        return False
    s = str(v).strip().lower()
    if s in ("true", "1", "yes", "y"):
        return True
    if s in ("false", "0", "no", "n", ""):
        return False
    raise ValidationError(f"invalid bool '{v}'")

def time_to_min(t: str) -> int:
    if not TIME_RE.match(t):
        raise ValidationError(f"invalid time format '{t}' expected HH:MM")
    h, m = t.split(":")
    h, m = int(h), int(m)
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValidationError(f"invalid time value '{t}'")
    return h * 60 + m

def load_csv(path: Path):
    if not path.exists():
        raise ValidationError(f"missing csv {path}")
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValidationError(f"empty csv {path}")
        rows = list(reader)
        # strip whitespace from all values
        for r in rows:
            for k in list(r.keys()):
                if r[k] is not None:
                    r[k] = r[k].strip()
        return reader.fieldnames, rows

def validate_unique(rows, key, path_name):
    seen = set()
    for i, r in enumerate(rows, start=2):
        k = r.get(key, "")
        if not k:
            raise ValidationError(f"{path_name}:{i} missing {key}")
        if k in seen:
            raise ValidationError(f"{path_name}:{i} duplicate {key}='{k}'")
        seen.add(k)
    return seen

def main(check: bool = False):
    # Check stale
    if check:
        if not JSON_DIR.exists():
            print("JSON dir missing, stale", file=sys.stderr)
            sys.exit(1)
        csv_mtime = max((p.stat().st_mtime for p in CSV_DIR.glob("*.csv")), default=0)
        json_files = list(JSON_DIR.glob("*.json"))
        if not json_files:
            print("no json files, stale", file=sys.stderr)
            sys.exit(1)
        json_mtime = min(p.stat().st_mtime for p in json_files)
        if csv_mtime > json_mtime:
            print(f"stale: csv newer ({csv_mtime}) than json ({json_mtime})", file=sys.stderr)
            sys.exit(1)
        print("JSON fresh vs CSV")
        return

    # Load
    _, routes = load_csv(CSV_DIR / "routes.csv")
    _, stops = load_csv(CSV_DIR / "stops.csv")
    _, route_stops = load_csv(CSV_DIR / "route_stops.csv")
    _, trips = load_csv(CSV_DIR / "trips.csv")
    _, stop_times = load_csv(CSV_DIR / "stop_times.csv")

    # Validate unique
    validate_unique(routes, "route_id", "routes.csv")
    validate_unique(stops, "stop_id", "stops.csv")
    validate_unique(trips, "trip_id", "trips.csv")

    # Build lookup sets
    route_ids = {r["route_id"] for r in routes}
    stop_ids = {s["stop_id"] for s in stops}
    trip_ids = {t["trip_id"] for t in trips}
    # Also map trip_id -> route_id
    trip_to_route = {t["trip_id"]: t["route_id"] for t in trips}

    # Validate FK: route_stops
    for i, rs in enumerate(route_stops, start=2):
        if rs["route_id"] not in route_ids:
            raise ValidationError(f"route_stops.csv:{i} unknown route_id '{rs['route_id']}'")
        if rs["stop_id"] not in stop_ids:
            raise ValidationError(f"route_stops.csv:{i} unknown stop_id '{rs['stop_id']}'")
        # seq int
        try:
            int(rs["seq"])
        except:
            raise ValidationError(f"route_stops.csv:{i} invalid seq '{rs['seq']}'")
        # is_inferred bool
        parse_bool(rs.get("is_inferred", "false"))

    # Validate seq continuous per route
    by_route = defaultdict(list)
    for rs in route_stops:
        by_route[rs["route_id"]].append(int(rs["seq"]))
    for rid, seqs in by_route.items():
        seqs_sorted = sorted(seqs)
        expected = list(range(1, len(seqs_sorted)+1))
        if seqs_sorted != expected:
            raise ValidationError(f"route_stops seq gap for route {rid}: got {seqs_sorted} expected {expected}")

    # Validate trips FK
    for i, t in enumerate(trips, start=2):
        if t["route_id"] not in route_ids:
            raise ValidationError(f"trips.csv:{i} unknown route_id '{t['route_id']}'")
        parse_bool(t.get("highlight", "false"))
        # departure_time
        if t["departure_time"]:
            time_to_min(t["departure_time"])
        # bus_no required
        if not t["bus_no"]:
            raise ValidationError(f"trips.csv:{i} missing bus_no")

    # Build route_stops membership map: route_id -> set(stop_id)
    route_to_stops = defaultdict(set)
    for rs in route_stops:
        route_to_stops[rs["route_id"]].add(rs["stop_id"])
    # Also map (trip_id -> route) -> stops set for validation
    # Validate stop_times
    seen_stop_time_key = set()
    for i, st in enumerate(stop_times, start=2):
        key = (st["trip_id"], st["stop_id"])
        if key in seen_stop_time_key:
            raise ValidationError(f"stop_times.csv:{i} duplicate trip+stop {key}")
        seen_stop_time_key.add(key)
        if st["trip_id"] not in trip_ids:
            raise ValidationError(f"stop_times.csv:{i} unknown trip_id '{st['trip_id']}'")
        if st["stop_id"] not in stop_ids:
            raise ValidationError(f"stop_times.csv:{i} unknown stop_id '{st['stop_id']}'")
        # validate membership: stop must be in route's stops
        rid = trip_to_route[st["trip_id"]]
        if st["stop_id"] not in route_to_stops.get(rid, set()):
            raise ValidationError(f"stop_times.csv:{i} stop '{st['stop_id']}' not in route_stops for route '{rid}' (trip {st['trip_id']})")
        time_to_min(st["arrival_time"])
        try:
            int(st["stop_seq"])
        except:
            raise ValidationError(f"stop_times.csv:{i} invalid stop_seq '{st['stop_seq']}'")

    # Validate monotone per trip
    by_trip = defaultdict(list)
    for st in stop_times:
        by_trip[st["trip_id"]].append(st)
    for tid, sts in by_trip.items():
        # sort by stop_seq
        sts_sorted = sorted(sts, key=lambda x: int(x["stop_seq"]))
        times = [time_to_min(s["arrival_time"]) for s in sts_sorted]
        for a, b in zip(times, times[1:]):
            if b < a:
                raise ValidationError(f"stop_times monotone violation trip {tid}: times {times}")

    # Derive halte_index: stop_id -> [route_id]
    halte_index = defaultdict(list)
    for rs in route_stops:
        if rs["route_id"] not in halte_index[rs["stop_id"]]:
            halte_index[rs["stop_id"]].append(rs["route_id"])
    # sort routes per stop
    for k in halte_index:
        halte_index[k] = sorted(halte_index[k])

    # Prepare output: ensure dirs
    JSON_DIR.mkdir(parents=True, exist_ok=True)
    GEO_DIR.mkdir(parents=True, exist_ok=True)

    # Write JSONs - preserve bool types for is_inferred/highlight
    # Helper to convert rows: keep raw strings but convert bools
    def convert_routes(rows):
        out = []
        for r in rows:
            out.append({
                "route_id": r["route_id"],
                "route_name": r["route_name"],
                "route_color_hex": r["route_color_hex"],
                "route_color_name": r["route_color_name"],
                "origin": r["origin"],
                "destination": r["destination"],
                "direction": r["direction"],
                "service_note": r["service_note"],
                "source_image": r["source_image"],
                "is_inferred": parse_bool(r.get("is_inferred", "false")),
            })
        return out

    def convert_stops(rows):
        out = []
        for r in rows:
            # lat/lng optional, empty -> None
            lat_raw = r.get("lat", "").strip()
            lng_raw = r.get("lng", "").strip()
            lat = None
            lng = None
            if lat_raw:
                try:
                    lat = float(lat_raw)
                    if not (-90 <= lat <= 90):
                        raise ValidationError(f"stops.csv invalid lat {lat_raw} for {r['stop_id']}")
                except ValueError:
                    raise ValidationError(f"stops.csv invalid lat {lat_raw}")
            if lng_raw:
                try:
                    lng = float(lng_raw)
                    if not (-180 <= lng <= 180):
                        raise ValidationError(f"stops.csv invalid lng {lng_raw} for {r['stop_id']}")
                except ValueError:
                    raise ValidationError(f"stops.csv invalid lng {lng_raw}")
            out.append({
                "stop_id": r["stop_id"],
                "stop_name_raw": r["stop_name_raw"],
                "stop_name_norm": r["stop_name_norm"],
                "stop_type": r["stop_type"],
                "transfer_type": r["transfer_type"],
                "lat": lat,
                "lng": lng,
                "notes": r["notes"],
            })
        return out

    def convert_route_stops(rows):
        out = []
        for r in rows:
            out.append({
                "route_id": r["route_id"],
                "stop_id": r["stop_id"],
                "seq": int(r["seq"]),
                "is_inferred": parse_bool(r.get("is_inferred", "false")),
                "notes": r["notes"],
            })
        out.sort(key=lambda x: (x["route_id"], x["seq"]))
        return out

    def convert_trips(rows):
        out = []
        for r in rows:
            out.append({
                "trip_id": r["trip_id"],
                "route_id": r["route_id"],
                "bus_no": r["bus_no"],
                "departure_time": r["departure_time"],
                "service_day": r["service_day"],
                "highlight": parse_bool(r.get("highlight", "false")),
                "notes": r["notes"],
            })
        return out

    def convert_stop_times(rows):
        out = []
        for r in rows:
            out.append({
                "trip_id": r["trip_id"],
                "stop_id": r["stop_id"],
                "arrival_time": r["arrival_time"],
                "stop_seq": int(r["stop_seq"]),
                "notes": r["notes"],
            })
        out.sort(key=lambda x: (x["trip_id"], x["stop_seq"]))
        return out

    routes_json = convert_routes(routes)
    stops_json = convert_stops(stops)
    route_stops_json = convert_route_stops(route_stops)
    trips_json = convert_trips(trips)
    stop_times_json = convert_stop_times(stop_times)

    with (JSON_DIR / "routes.json").open("w", encoding="utf-8") as f:
        json.dump(routes_json, f, indent=2, ensure_ascii=False)
    with (JSON_DIR / "stops.json").open("w", encoding="utf-8") as f:
        json.dump(stops_json, f, indent=2, ensure_ascii=False)
    with (JSON_DIR / "route_stops.json").open("w", encoding="utf-8") as f:
        json.dump(route_stops_json, f, indent=2, ensure_ascii=False)
    with (JSON_DIR / "trips.json").open("w", encoding="utf-8") as f:
        json.dump(trips_json, f, indent=2, ensure_ascii=False)
    with (JSON_DIR / "stop_times.json").open("w", encoding="utf-8") as f:
        json.dump(stop_times_json, f, indent=2, ensure_ascii=False)
    with (JSON_DIR / "halte_index.json").open("w", encoding="utf-8") as f:
        json.dump(dict(halte_index), f, indent=2, ensure_ascii=False)

    # build_meta
    inferred_routes = sum(1 for r in routes if parse_bool(r.get("is_inferred","false")))
    inferred_route_stops = sum(1 for rs in route_stops if parse_bool(rs.get("is_inferred","false")))
    meta = {
        "counts": {
            "routes": len(routes),
            "stops": len(stops),
            "route_stops": len(route_stops),
            "trips": len(trips),
            "stop_times": len(stop_times),
            "inferred_routes": inferred_routes,
            "inferred_route_stops": inferred_route_stops,
        },
        "routes_inferred": [r["route_id"] for r in routes if parse_bool(r.get("is_inferred","false"))],
        "generated_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
    }
    with (JSON_DIR / "build_meta.json").open("w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    # geo generation - points for stops, lines for routes where coords available
    stop_coord = {s["stop_id"]: (s["lng"], s["lat"]) for s in stops_json if s["lat"] is not None and s["lng"] is not None}
    features = []
    # stop points
    for s in stops_json:
        if s["lat"] is not None and s["lng"] is not None:
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [s["lng"], s["lat"]]},
                "properties": {"stop_id": s["stop_id"], "name": s["stop_name_raw"], "type": s["stop_type"], "inferred": False}
            })
    # route lines
    by_route_rs = defaultdict(list)
    for rs in route_stops_json:
        by_route_rs[rs["route_id"]].append(rs)
    route_meta = {r["route_id"]: r for r in routes_json}
    for rid, rss in by_route_rs.items():
        rss_sorted = sorted(rss, key=lambda x: x["seq"])
        coords = []
        missing = 0
        for rs in rss_sorted:
            coord = stop_coord.get(rs["stop_id"])
            if coord and coord[0] is not None:
                coords.append(list(coord))
            else:
                missing += 1
        if len(coords) >= 2:
            features.append({
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": coords},
                "properties": {
                    "route_id": rid,
                    "route_name": route_meta.get(rid, {}).get("route_name",""),
                    "color": route_meta.get(rid, {}).get("route_color_hex",""),
                    "is_inferred": route_meta.get(rid, {}).get("is_inferred", False),
                    "missing_coords": missing
                }
            })
    geo = {
        "type": "FeatureCollection",
        "features": features,
        "note": "generated from stops.csv lat/lng + route_stops order"
    }
    with (GEO_DIR / "routes.geojson").open("w", encoding="utf-8") as f:
        json.dump(geo, f, indent=2, ensure_ascii=False)

    print(f"build ok: routes={len(routes)} stops={len(stops)} route_stops={len(route_stops)} trips={len(trips)} stop_times={len(stop_times)} inferred_routes={inferred_routes}")
    print(f"halte_index stops={len(halte_index)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="check JSON stale vs CSV")
    args = parser.parse_args()
    try:
        main(check=args.check)
    except ValidationError as e:
        print(f"validation error: {e}", file=sys.stderr)
        sys.exit(1)
