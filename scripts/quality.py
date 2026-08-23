#!/usr/bin/env python3
"""
Quality checks for B-full - timetable accuracy.

- per route delta stats (min, max, avg, variance)
- flags uniform +2min synthetic vs observed variance 1-4min
- highlight coverage
- inferred coverage
- monotone check (already in build.py)
"""
import json, pathlib, csv
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
JDIR = ROOT / "data" / "json"
CSV_DIR = ROOT / "data" / "csv"

def time_to_min(t):
    h,m=map(int,t.split(":"))
    return h*60+m

def main():
    trips = json.load(open(JDIR/"trips.json"))
    stop_times = json.load(open(JDIR/"stop_times.json"))
    route_stops = json.load(open(JDIR/"route_stops.json"))

    by_trip = defaultdict(list)
    for st in stop_times:
        by_trip[st["trip_id"]].append(st)
    by_route = defaultdict(list)
    for rs in route_stops:
        by_route[rs["route_id"]].append(rs)

    print("=== Per route delta stats ===")
    for rid, rss in sorted(by_route.items()):
        if rid=="INT_VANYA_INT":
            continue
        deltas=[]
        for trip_id, sts in by_trip.items():
            # filter sts that belong to this route via trip lookup
            trip_route = next((t["route_id"] for t in trips if t["trip_id"]==trip_id), None)
            if trip_route != rid:
                continue
            sts_sorted = sorted(sts, key=lambda x: x["stop_seq"])
            for a,b in zip(sts_sorted, sts_sorted[1:]):
                d = time_to_min(b["arrival_time"]) - time_to_min(a["arrival_time"])
                deltas.append(d)
        if deltas:
            avg = sum(deltas)/len(deltas)
            print(f"{rid}: n={len(deltas)} avg={avg:.1f} min={min(deltas)} max={max(deltas)} variance={max(deltas)-min(deltas)}")
            if max(deltas)-min(deltas)==0:
                print(f"  -> FLAG uniform synthetic +2min, expected variance 1-4 per B-light")
        else:
            print(f"{rid}: no deltas")

    print("\n=== Highlight coverage ===")
    by_route_trips = defaultdict(list)
    for t in trips:
        by_route_trips[t["route_id"]].append(t)
    for rid, lst in sorted(by_route_trips.items()):
        hl = sum(1 for x in lst if x["highlight"])
        print(f"{rid}: {hl}/{len(lst)} highlighted ({hl/len(lst)*100:.0f}%)")

    print("\n=== Inferred ===")
    routes=json.load(open(JDIR/"routes.json"))
    for r in routes:
        if r["is_inferred"]:
            print(f"inferred route {r['route_id']} {r['route_name']}")

    print("\n=== Monotone already validated in build.py ===")

if __name__ == "__main__":
    main()
