#!/usr/bin/env python3
"""
Patch B-full - apply realistic deltas per route to stop_times.csv

Example: python scripts/patch_bfull.py --route INT_SEKT13
"""

import argparse
import csv
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
CSV = ROOT / "data" / "csv" / "stop_times.csv"

# per route delta profiles: list of deltas per hop (len = stops), first 0 for origin
PROFILES = {
    "INT_SEKT13": [0, 3, 4, 2, 2, 3, 4, 1, 2, 1, 5, 1],  # 12 stops
    "SEKT13_INT": [0, 1, 3, 2, 2, 2, 1, 2, 3, 4, 2],  # 11 stops
    "GRN_SEKT13": [0, 1, 2, 1, 3, 4, 2, 3, 2, 4],  # 10 stops
    "SEKT13_GRN": [0, 1, 3, 2, 2, 1, 2, 1, 4, 2],  # 10 stops
    "INT_DEPARK_R1": [0, 3, 2, 4, 1, 5, 3, 2, 1, 2, 1, 2],  # 12 stops
    "INT_DEPARK_R2": [0, 3, 2, 2, 2, 2, 5, 4, 2, 1, 2, 3, 2],  # 13 stops
    "BREEZE_AEON_ICE": [0, 2, 1, 1, 2, 1, 2, 2, 1, 1, 4, 1],  # 12 stops
    "INT_BREEZE_INT": [0, 4, 5, 1, 3, 1, 2, 4, 1, 1, 2, 2, 3],  # 13 stops (loop closure implicit)
}


def time_to_min(t):
    h, m = map(int, t.split(":"))
    return h * 60 + m


def min_to_time(m):
    return f"{m // 60:02d}:{m % 60:02d}"


def patch(route_id):
    deltas = PROFILES.get(route_id)
    if not deltas:
        print(f"no profile for {route_id}, available {list(PROFILES.keys())}")
        return

    rows = []
    with open(CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # group by trip
    from collections import defaultdict

    by_trip = defaultdict(list)
    for r in rows:
        by_trip[r["trip_id"]].append(r)

    # need trip->route lookup
    trips = []
    with open(ROOT / "data/csv/trips.csv", newline="", encoding="utf-8") as f:
        trips = list(csv.DictReader(f))
    trip_to_route = {t["trip_id"]: t["route_id"] for t in trips}

    patched = 0
    for trip_id, sts in by_trip.items():
        if trip_to_route.get(trip_id) != route_id:
            continue
        sts_sorted = sorted(sts, key=lambda x: int(x["stop_seq"]))
        # find departure time for this trip
        dep = next((t["departure_time"] for t in trips if t["trip_id"] == trip_id), None)
        if not dep:
            continue
        base = time_to_min(dep)
        # cumulative deltas
        cum = 0
        for i, st in enumerate(sts_sorted):
            if i < len(deltas):
                cum = sum(deltas[: i + 1])  # deltas[0]=0 for first stop
            # deltas includes 0 for first, so first stop cum 0
            # adjust: for seq1 cum 0, seq2 cum 3, seq3 cum 7, etc.
            # our deltas list already 0 at 0, so cumulative works
            new_time = min_to_time(base + cum)
            # update in rows
            for r in rows:
                if r["trip_id"] == trip_id and r["stop_id"] == st["stop_id"]:
                    r["arrival_time"] = new_time
                    patched += 1
                    break

    with open(CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f, fieldnames=["trip_id", "stop_id", "arrival_time", "stop_seq", "notes"]
        )
        w.writeheader()
        w.writerows(rows)
    print(f"patched {patched} rows for {route_id} with deltas {deltas}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--route", help="route_id to patch")
    ap.add_argument("--all", action="store_true", help="patch all profiles")
    args = ap.parse_args()
    if args.all:
        for rid in PROFILES:
            patch(rid)
    elif args.route:
        patch(args.route)
    else:
        print("specify --route or --all")
