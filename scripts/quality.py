#!/usr/bin/env python3
"""
Quality checks for B-full - timetable accuracy.

- per route delta stats (min, max, avg, variance)
- flags uniform +2min synthetic vs observed variance 1-4min
- highlight coverage
- inferred coverage
- monotone check (already in build.py)
"""

from __future__ import annotations

import json
import pathlib
from collections import defaultdict
from typing import Any, Dict, List

ROOT = pathlib.Path(__file__).resolve().parents[1]
JDIR = ROOT / "data" / "json"
CSV_DIR = ROOT / "data" / "csv"


def time_to_min(t: str) -> int:
    h_str, m_str = t.split(":")
    h, m = int(h_str), int(m_str)
    return h * 60 + m


def main() -> None:
    trips: List[Dict[str, Any]] = json.load(open(JDIR / "trips.json", encoding="utf-8"))
    stop_times: List[Dict[str, Any]] = json.load(open(JDIR / "stop_times.json", encoding="utf-8"))
    route_stops: List[Dict[str, Any]] = json.load(open(JDIR / "route_stops.json", encoding="utf-8"))

    by_trip: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for st in stop_times:
        by_trip[str(st["trip_id"])].append(st)
    by_route: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for rs in route_stops:
        by_route[str(rs["route_id"])].append(rs)

    print("=== Per route delta stats ===")
    for rid, rss in sorted(by_route.items()):
        if rid == "INT_VANYA_INT":
            continue
        deltas: List[int] = []
        for trip_id, sts in by_trip.items():
            trip_route: str | None = next(
                (str(t["route_id"]) for t in trips if str(t["trip_id"]) == trip_id), None
            )
            if trip_route != rid:
                continue
            sts_sorted: List[Dict[str, Any]] = sorted(sts, key=lambda x: int(str(x["stop_seq"])))
            for a, b in zip(sts_sorted, sts_sorted[1:]):
                d: int = time_to_min(str(b["arrival_time"])) - time_to_min(str(a["arrival_time"]))
                deltas.append(d)
        if deltas:
            avg: float = sum(deltas) / len(deltas)
            print(
                f"{rid}: n={len(deltas)} avg={avg:.1f} min={min(deltas)} max={max(deltas)} variance={max(deltas) - min(deltas)}"
            )
            if max(deltas) - min(deltas) == 0:
                print("  -> FLAG uniform synthetic +2min, expected variance 1-4 per B-light")
        else:
            print(f"{rid}: no deltas")

    print("\n=== Highlight coverage ===")
    by_route_trips: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for t in trips:
        by_route_trips[str(t["route_id"])].append(t)
    for rid_item, lst in sorted(by_route_trips.items()):
        hl: int = sum(1 for x in lst if bool(x["highlight"]))
        print(f"{rid_item}: {hl}/{len(lst)} highlighted ({hl / len(lst) * 100:.0f}%)")

    print("\n=== Inferred ===")
    routes: List[Dict[str, Any]] = json.load(open(JDIR / "routes.json", encoding="utf-8"))
    for r in routes:
        if bool(r["is_inferred"]):
            print(f"inferred route {r['route_id']} {r['route_name']}")

    print("\n=== Monotone already validated in build.py ===")


if __name__ == "__main__":
    main()
