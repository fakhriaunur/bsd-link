#!/usr/bin/env python3
"""
Patch B-full - apply realistic deltas per route to stop_times.csv

Example: python scripts/patch_bfull.py --route INT_SEKT13
"""

from __future__ import annotations

import argparse
import csv
import pathlib
from collections import defaultdict
from typing import Dict, List

ROOT = pathlib.Path(__file__).resolve().parents[1]
CSV = ROOT / "data" / "csv" / "stop_times.csv"

# per route delta profiles: list of deltas per hop (len = stops), first 0 for origin
PROFILES: Dict[str, List[int]] = {
    "INT_SEKT13": [0, 3, 4, 2, 2, 3, 4, 1, 2, 1, 5, 1],  # 12 stops
    "SEKT13_INT": [0, 1, 3, 2, 2, 2, 1, 2, 3, 4, 2],  # 11 stops
    "GRN_SEKT13": [0, 1, 2, 1, 3, 4, 2, 3, 2, 4],  # 10 stops
    "SEKT13_GRN": [0, 1, 3, 2, 2, 1, 2, 1, 4, 2],  # 10 stops
    "INT_DEPARK_R1": [0, 3, 2, 4, 1, 5, 3, 2, 1, 2, 1, 2],  # 12 stops
    "INT_DEPARK_R2": [0, 3, 2, 2, 2, 2, 5, 4, 2, 1, 2, 3, 2],  # 13 stops
    "BREEZE_AEON_ICE": [0, 2, 1, 1, 2, 1, 2, 2, 1, 1, 4, 1],  # 12 stops
    "INT_BREEZE_INT": [0, 4, 5, 1, 3, 1, 2, 4, 1, 1, 2, 2, 3],  # 13 stops (loop closure implicit)
}


def time_to_min(t: str) -> int:
    h_str, m_str = t.split(":")
    h, m = int(h_str), int(m_str)
    return h * 60 + m


def min_to_time(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


def patch(route_id: str) -> None:
    deltas: List[int] | None = PROFILES.get(route_id)
    if not deltas:
        print(f"no profile for {route_id}, available {list(PROFILES.keys())}")
        return

    rows: List[Dict[str, str]] = []
    with open(CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames is not None
        rows = [dict(r) for r in reader]

    by_trip: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for r in rows:
        by_trip[r["trip_id"]].append(r)

    trips: List[Dict[str, str]] = []
    with open(ROOT / "data/csv/trips.csv", newline="", encoding="utf-8") as f:
        reader2 = csv.DictReader(f)
        assert reader2.fieldnames is not None
        trips = [dict(r) for r in reader2]
    trip_to_route: Dict[str, str] = {t["trip_id"]: t["route_id"] for t in trips}

    patched = 0
    for trip_id, sts in by_trip.items():
        if trip_to_route.get(trip_id) != route_id:
            continue
        sts_sorted: List[Dict[str, str]] = sorted(sts, key=lambda x: int(x["stop_seq"]))
        dep: str | None = next(
            (t["departure_time"] for t in trips if t["trip_id"] == trip_id), None
        )
        if not dep:
            continue
        base: int = time_to_min(dep)
        cum = 0
        for i, st in enumerate(sts_sorted):
            if i < len(deltas):
                cum = sum(deltas[: i + 1])
            new_time: str = min_to_time(base + cum)
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


def main() -> None:
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


if __name__ == "__main__":
    main()
