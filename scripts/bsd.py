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

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any, Dict, List, Tuple

ROOT = pathlib.Path(__file__).resolve().parents[1]
JDIR = ROOT / "data" / "json"

import route


def load_data() -> Tuple[
    List[Dict[str, Any]],
    List[Dict[str, Any]],
    List[Dict[str, Any]],
    Dict[str, List[str]],
    List[Dict[str, Any]],
    List[Dict[str, Any]],
]:
    rs: List[Dict[str, Any]] = json.load(open(JDIR / "route_stops.json", encoding="utf-8"))
    st: List[Dict[str, Any]] = json.load(open(JDIR / "stop_times.json", encoding="utf-8"))
    tr: List[Dict[str, Any]] = json.load(open(JDIR / "trips.json", encoding="utf-8"))
    hi: Dict[str, List[str]] = json.load(open(JDIR / "halte_index.json", encoding="utf-8"))
    routes: List[Dict[str, Any]] = json.load(open(JDIR / "routes.json", encoding="utf-8"))
    stops: List[Dict[str, Any]] = json.load(open(JDIR / "stops.json", encoding="utf-8"))
    return rs, st, tr, hi, routes, stops


def parse_yaml_simple(text: str) -> Dict[str, Any]:
    """Minimal yaml parser for our scenario files - handles strings, lists, bools, nested walk_edges"""
    import re

    data: Dict[str, Any] = {}
    lines: List[str] = text.splitlines()
    i = 0
    current_walk: Dict[str, Any] | None = None
    in_walk = False
    while i < len(lines):
        line: str = lines[i].rstrip()
        if not line or line.strip().startswith("#"):
            i += 1
            continue
        if line.strip().startswith("walk_edges:"):
            in_walk = True
            if "[]" in line:
                data["walk_edges"] = []
                in_walk = False
            else:
                data["walk_edges"] = []
            i += 1
            continue
        if in_walk:
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
            if re.match(r"^\w+:", line):
                in_walk = False
                continue
            i += 1
            continue
        m2 = re.match(r"^(\w+):\s*(.*)", line)
        if m2:
            k: str = m2.group(1)
            v: str = m2.group(2).strip()
            if k == "destinations":
                v_stripped: str = v.strip()
                if v_stripped.startswith("["):
                    inner: str = v_stripped[1:-1]
                    items: List[str] = [x.strip() for x in inner.split(",") if x.strip()]
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


def load_scenario(path: str) -> Dict[str, Any]:
    text: str = pathlib.Path(path).read_text(encoding="utf-8")
    try:
        import yaml

        data: Any = yaml.safe_load(text)
        if isinstance(data, dict):
            result: Dict[str, Any] = dict(data)
            if "walk_edges" in result and result["walk_edges"] is None:
                result["walk_edges"] = []
            return result
        return {}
    except Exception:
        return parse_yaml_simple(text)


def do_halte(stop_id: str) -> None:
    _, _, _, hi, routes, _stops = load_data()
    routes_for: List[str] | None = hi.get(stop_id)
    if not routes_for:
        print(f"no routes for halte {stop_id}")
        sys.exit(1)
    print(f"{stop_id} served by {len(routes_for)} routes:")
    route_map: Dict[str, Dict[str, Any]] = {str(r["route_id"]): r for r in routes}
    for rid in routes_for:
        r: Dict[str, Any] = route_map.get(rid, {})
        print(f"  {rid} {r.get('route_name', '')} {r.get('route_color_hex', '')}")


def do_next(stop_id: str, time_str: str) -> None:
    _, st, _tr, _, _, _ = load_data()
    target: int = route.time_to_min(time_str)
    cands: List[Tuple[int, Dict[str, Any]]] = []
    for s in st:
        if str(s["stop_id"]) == stop_id:
            t: int = route.time_to_min(str(s["arrival_time"]))
            if t >= target:
                cands.append((t, s))
    cands.sort(key=lambda x: x[0])
    if not cands:
        print(f"no departures from {stop_id} after {time_str}")
        return
    print(f"next 5 from {stop_id} after {time_str}:")
    for _t, s in cands[:5]:
        print(f"  {s['arrival_time']} trip {s['trip_id']} seq {s['stop_seq']}")


def do_scenario(scenario_path: str) -> None:
    rs, st, tr, _hi, _routes, _stops = load_data()
    scenario: Dict[str, Any] = load_scenario(scenario_path)
    if "origin" not in scenario or "destinations" not in scenario:
        print(f"invalid scenario {scenario_path}: missing origin/destinations")
        sys.exit(1)
    res: Dict[str, Any] = route.solve_scenario(scenario, rs, st, tr)
    if "error" in res:
        print(json.dumps(res, indent=2))
        sys.exit(1)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    print("\nSummary:")
    print(f"  Scenario: {res['scenario']} goal={res['goal']}")
    origin: str = str(res["origin"])
    dest_ordered: List[str] = [str(x) for x in res["destinations_ordered"]]
    ret: bool = bool(res["return_to_origin"])
    seq_parts: List[str] = [origin] + dest_ordered + ([origin] if ret else [])
    print(f"  Order: {' -> '.join(seq_parts)}")
    print(f"  Total time {res['total_time']}min transfers {res['total_transfers']}")
    legs: List[Dict[str, Any]] = res["legs"]
    for leg in legs:
        print(f"  leg {leg['from']} -> {leg['to']}: {leg['time']}min {leg['transfers']} transfers")
        path: List[str] = leg["path"]
        path_stops: List[str] = [str(p).rsplit("__", 1)[0] for p in path]
        print(f"    path: {' -> '.join(path_stops)}")


def main() -> None:
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
        do_halte(str(args.halte))
    elif args.next:
        do_next(str(args.next), str(args.time))
    elif args.scenario:
        do_scenario(str(args.scenario))
    elif args.list_routes:
        _, _, _, _, routes, _ = load_data()
        for r in routes:
            print(
                f"{r['route_id']} {r['route_name']} {r['route_color_hex']} inferred={r['is_inferred']}"
            )
    elif args.list_stops:
        _, _, _, hi, _, stops = load_data()
        for s in stops:
            cnt: int = len(hi.get(str(s["stop_id"]), []))
            print(f"{s['stop_id']} {s['stop_name_raw']} routes={cnt} type={s['stop_type']}")
    else:
        p.print_help()


if __name__ == "__main__":
    main()
