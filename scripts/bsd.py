#!/usr/bin/env python3
"""
BSD Link CLI - thin shell over route pure core.

Usage:
  python scripts/bsd.py --halte THE_BREEZE
  python scripts/bsd.py --next PASAR_MODERN --time 07:00
  python scripts/bsd.py --scenario scenarios/intermoda-aeon-breeze-icon-least-transfer.yaml
  python scripts/bsd.py --list-routes
  python scripts/bsd.py --list-stops

No external deps; yaml parsed via fallback if pyyaml missing.
"""

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
JDIR = ROOT / "data" / "json"

# pure core
import route


def load_data():
    rs = json.load(open(JDIR / "route_stops.json"))
    st = json.load(open(JDIR / "stop_times.json"))
    tr = json.load(open(JDIR / "trips.json"))
    hi = json.load(open(JDIR / "halte_index.json"))
    routes = json.load(open(JDIR / "routes.json"))
    stops = json.load(open(JDIR / "stops.json"))
    return rs, st, tr, hi, routes, stops


def parse_yaml_simple(text):
    """Minimal yaml parser for our scenario files - handles strings, lists, bools, nested walk_edges"""
    import re

    data = {}
    lines = text.splitlines()
    i = 0
    current_walk = None
    in_walk = False
    while i < len(lines):
        line = lines[i].rstrip()
        if not line or line.strip().startswith("#"):
            i += 1
            continue
        if line.strip().startswith("walk_edges:"):
            in_walk = True
            # check if empty list
            if "[]" in line:
                data["walk_edges"] = []
                in_walk = False
            else:
                data["walk_edges"] = []
            i += 1
            continue
        if in_walk:
            # walk entry: lines starting with "  - from:" or "    to:"
            m = re.match(r"\s*-\s*from:\s*(.+)", line)
            if m:
                current_walk = {"from": m.group(1).strip()}
                data["walk_edges"].append(current_walk)
                i += 1
                continue
            m = re.match(r"\s*to:\s*(.+)", line)
            if m and current_walk is not None:
                current_walk["to"] = m.group(1).strip()
                i += 1
                continue
            m = re.match(r"\s*minutes:\s*(.+)", line)
            if m and current_walk is not None:
                current_walk["minutes"] = int(m.group(1).strip())
                i += 1
                continue
            m = re.match(r"\s*note:\s*(.+)", line)
            if m and current_walk is not None:
                current_walk["note"] = m.group(1).strip()
                i += 1
                continue
            # empty or next top-level key
            if re.match(r"^\w+:", line):
                in_walk = False
                continue
            i += 1
            continue
        m = re.match(r"^(\w+):\s*(.*)", line)
        if m:
            k, v = m.group(1), m.group(2).strip()
            if k == "destinations":
                # parse [ICON, AEON_MALL_2, THE_BREEZE]
                v = v.strip()
                if v.startswith("["):
                    inner = v[1:-1]
                    items = [x.strip() for x in inner.split(",") if x.strip()]
                    data[k] = items
                else:
                    data[k] = []
            elif v.lower() in ("true", "false"):
                data[k] = v.lower() == "true"
            elif v == "[]":
                data[k] = []
            else:
                data[k] = v
        i += 1
    return data


def load_scenario(path):
    text = pathlib.Path(path).read_text(encoding="utf-8")
    # try pyyaml first
    try:
        import yaml

        data = yaml.safe_load(text)
        # yaml may parse walk_edges already
        if "walk_edges" in data and data["walk_edges"] is None:
            data["walk_edges"] = []
        return data
    except Exception:
        return parse_yaml_simple(text)


def do_halte(stop_id):
    _, _, _, hi, routes, stops = load_data()
    routes_for = hi.get(stop_id)
    if not routes_for:
        print(f"no routes for halte {stop_id}")
        sys.exit(1)
    print(f"{stop_id} served by {len(routes_for)} routes:")
    route_map = {r["route_id"]: r for r in routes}
    for rid in routes_for:
        r = route_map.get(rid, {})
        print(f"  {rid} {r.get('route_name', '')} {r.get('route_color_hex', '')}")


def do_next(stop_id, time_str):
    _, st, tr, _, _, _ = load_data()
    # find trips that stop at stop_id, arrival >= time_str
    target = route.time_to_min(time_str)
    cands = []
    for s in st:
        if s["stop_id"] == stop_id:
            t = route.time_to_min(s["arrival_time"])
            if t >= target:
                cands.append((t, s))
    cands.sort(key=lambda x: x[0])
    if not cands:
        print(f"no departures from {stop_id} after {time_str}")
        return
    print(f"next 5 from {stop_id} after {time_str}:")
    for t, s in cands[:5]:
        print(f"  {s['arrival_time']} trip {s['trip_id']} seq {s['stop_seq']}")


def do_scenario(scenario_path):
    rs, st, tr, hi, routes, stops = load_data()
    scenario = load_scenario(scenario_path)
    # ensure required keys
    if "origin" not in scenario or "destinations" not in scenario:
        print(f"invalid scenario {scenario_path}: missing origin/destinations")
        sys.exit(1)
    res = route.solve_scenario(scenario, rs, st, tr)
    if "error" in res:
        print(json.dumps(res, indent=2))
        sys.exit(1)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    # human summary
    print("\nSummary:")
    print(f"  Scenario: {res['scenario']} goal={res['goal']}")
    print(
        f"  Order: {' -> '.join([res['origin']] + res['destinations_ordered'] + ([res['origin']] if res['return_to_origin'] else []))}"
    )
    print(f"  Total time {res['total_time']}min transfers {res['total_transfers']}")
    for leg in res["legs"]:
        print(f"  leg {leg['from']} -> {leg['to']}: {leg['time']}min {leg['transfers']} transfers")
        # print path stops only
        path_stops = [p.rsplit("__", 1)[0] for p in leg["path"]]
        print(f"    path: {' -> '.join(path_stops)}")


def main():
    p = argparse.ArgumentParser(description="BSD Link CLI")
    p.add_argument("--halte", help="show routes serving halte")
    p.add_argument("--next", help="halte for next departures")
    p.add_argument("--time", help="time HH:MM for --next", default="07:00")
    p.add_argument("--scenario", help="path to scenario yaml")
    p.add_argument("--list-routes", action="store_true", help="list all routes")
    p.add_argument(
        "--list-stops", action="store_true", help="list all stops with halte_index count"
    )
    args = p.parse_args()

    if args.halte:
        do_halte(args.halte)
    elif args.next:
        do_next(args.next, args.time)
    elif args.scenario:
        do_scenario(args.scenario)
    elif args.list_routes:
        _, _, _, _, routes, _ = load_data()
        for r in routes:
            print(
                f"{r['route_id']} {r['route_name']} {r['route_color_hex']} inferred={r['is_inferred']}"
            )
    elif args.list_stops:
        _, _, _, hi, _, stops = load_data()
        for s in stops:
            cnt = len(hi.get(s["stop_id"], []))
            print(f"{s['stop_id']} {s['stop_name_raw']} routes={cnt} type={s['stop_type']}")
    else:
        p.print_help()


if __name__ == "__main__":
    main()
