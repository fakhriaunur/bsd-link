#!/usr/bin/env python3
"""
Route pure core - no IO, no side effects.
Builds expanded graph from route_stops + stop_times, solves scenarios.

Node = "STOP_ID__ROUTE_ID"  (stop on specific route). Transfer edges connect same STOP across routes.
Edge weights: time (minutes), transfers (0 or 1). Dijkstra uses tuple cost for lexicographic goals.

DDD: Routing bounded context, Scenario aggregate owns origin/destinations/goal.
APOSD: deep module hides graph expansion, exposes find_best_route(scenario, data).
"""

from __future__ import annotations

import heapq
import itertools
from collections import defaultdict
from typing import Any, Dict, List, Set, Tuple

Node = str
Edge = Tuple[Node, int, int, str]  # neighbor, time, transfers, label


def time_to_min(t: str) -> int:
    h, m = map(int, t.split(":"))
    return h * 60 + m


def build_travel_times(
    route_stops: List[Dict[str, Any]], stop_times: List[Dict[str, Any]]
) -> Dict[Tuple[str, str, str], int]:
    """
    Avg travel minutes per consecutive pair per route.
    route_stops: list of {route_id, stop_id, seq}
    stop_times: list of {trip_id, stop_id, arrival_time, stop_seq}
    Returns dict (route_id, from_stop, to_stop) -> avg_min
    """
    by_trip: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for st in stop_times:
        by_trip[str(st["trip_id"])].append(st)
    route_pairs: Set[Tuple[str, str, str]] = set()
    by_route: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for rs in route_stops:
        by_route[str(rs["route_id"])].append(rs)
    for rid, rss in by_route.items():
        rss_sorted: List[Dict[str, Any]] = sorted(rss, key=lambda x: int(str(x["seq"])))
        for a, b in zip(rss_sorted, rss_sorted[1:]):
            route_pairs.add((rid, str(a["stop_id"]), str(b["stop_id"])))

    deltas: Dict[Tuple[str, str, str], List[int]] = defaultdict(list)
    for _trip_id, sts in by_trip.items():
        sts_sorted: List[Dict[str, Any]] = sorted(sts, key=lambda x: int(str(x["stop_seq"])))
        for a, b in zip(sts_sorted, sts_sorted[1:]):
            for rid in set(
                str(r["route_id"])
                for r in route_stops
                if str(r["stop_id"]) in (str(a["stop_id"]), str(b["stop_id"]))
            ):
                if (rid, str(a["stop_id"]), str(b["stop_id"])) in route_pairs:
                    delta: int = time_to_min(str(b["arrival_time"])) - time_to_min(
                        str(a["arrival_time"])
                    )
                    if delta >= 0:
                        deltas[(rid, str(a["stop_id"]), str(b["stop_id"]))].append(delta)
    avg: Dict[Tuple[str, str, str], int] = {}
    for k, lst in deltas.items():
        avg[k] = sum(lst) // len(lst) if lst else 2
    for rp in route_pairs:
        if rp not in avg:
            avg[rp] = 2
    return avg


def compute_headway_wait(trips: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    per route avg headway/2 wait minutes. trips: list {route_id, departure_time}
    Returns dict route_id -> wait_min
    """
    by_route: Dict[str, List[int]] = defaultdict(list)
    for t in trips:
        by_route[str(t["route_id"])].append(time_to_min(str(t["departure_time"])))
    waits: Dict[str, int] = {}
    for rid, times in by_route.items():
        times_sorted: List[int] = sorted(times)
        if len(times_sorted) < 2:
            waits[rid] = 15
            continue
        diffs: List[int] = [b - a for a, b in zip(times_sorted, times_sorted[1:]) if b > a]
        avg_headway: int = sum(diffs) // len(diffs) if diffs else 30
        waits[rid] = max(5, avg_headway // 2)
    return waits


def build_expanded_graph(
    route_stops: List[Dict[str, Any]],
    stop_times: List[Dict[str, Any]],
    trips: List[Dict[str, Any]],
    walk_edges: List[Dict[str, Any]] | None = None,
) -> Tuple[Dict[Node, List[Edge]], Dict[str, int], Dict[Tuple[str, str, str], int]]:
    """
    Returns adjacency dict Node -> list[Edge]
    walk_edges: list {from, to, minutes}
    """
    if walk_edges is None:
        walk_edges = []
    travel: Dict[Tuple[str, str, str], int] = build_travel_times(route_stops, stop_times)
    waits: Dict[str, int] = compute_headway_wait(trips)

    nodes: Set[Node] = set()
    by_stop: Dict[str, List[Node]] = defaultdict(list)
    for rs in route_stops:
        nid: Node = f"{rs['stop_id']}__{rs['route_id']}"
        nodes.add(nid)
        by_stop[str(rs["stop_id"])].append(nid)

    adj: Dict[Node, List[Edge]] = {n: [] for n in nodes}

    by_route: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for rs in route_stops:
        by_route[str(rs["route_id"])].append(rs)
    for rid, rss in by_route.items():
        rss_sorted: List[Dict[str, Any]] = sorted(rss, key=lambda x: int(str(x["seq"])))
        for a, b in zip(rss_sorted, rss_sorted[1:]):
            u: Node = f"{a['stop_id']}__{rid}"
            v: Node = f"{b['stop_id']}__{rid}"
            t: int = travel.get((rid, str(a["stop_id"]), str(b["stop_id"])), 2)
            adj[u].append((v, t, 0, rid))

    for stop_id, nids in by_stop.items():
        if len(nids) < 2:
            continue
        for u in nids:
            _, ru = u.rsplit("__", 1)
            for v in nids:
                if u == v:
                    continue
                _, rv = v.rsplit("__", 1)
                wait_mins: int = waits.get(rv, 15)
                adj[u].append((v, wait_mins, 1, f"transfer:{ru}->{rv}"))

    for we in walk_edges:
        walk_from: str = str(we["from"])
        walk_to: str = str(we["to"])
        mins: int = int(str(we["minutes"]))
        for u in by_stop.get(walk_from, []):
            for v in by_stop.get(walk_to, []):
                if u == v:
                    continue
                adj[u].append((v, mins, 0, f"walk:{walk_from}->{walk_to}"))
    return adj, waits, travel


def dijkstra(
    adj: Dict[Node, List[Edge]],
    start_nodes: List[Node],
    goal_stop: str,
    goal_mode: str = "least-time",
) -> Tuple[int, int, List[Node]] | None:
    """
    goal_stop: stop_id to reach (any route)
    goal_mode: least-transfer (primary transfers), least-time (primary time)
    Returns (total_time, transfers, path_nodes) or None
    """
    pq: List[Tuple[int, int, Node, List[Node], int, int]] = []
    best: Dict[Node, Tuple[int, int]] = {}
    for s in start_nodes:
        heapq.heappush(pq, (0, 0, s, [s], 0, 0))

    visited: Set[Node] = set()
    while pq:
        if goal_mode == "least-transfer":
            transfers, time, node, path, tr, ti = heapq.heappop(pq)
        else:
            time, transfers, node, path, tr, ti = heapq.heappop(pq)

        stop_part: str = node.rsplit("__", 1)[0]
        if stop_part == goal_stop:
            return ti, tr, path

        if node in visited:
            continue
        visited.add(node)

        for nbr, wt, wf, _label in adj.get(node, []):
            if nbr in visited:
                continue
            nti: int = ti + wt
            ntr: int = tr + wf
            if nbr in best and best[nbr][0] <= ntr and best[nbr][1] <= nti:
                pass
            best[nbr] = (ntr, nti)
            if goal_mode == "least-transfer":
                heapq.heappush(pq, (ntr, nti, nbr, path + [nbr], ntr, nti))
            else:
                heapq.heappush(pq, (nti, ntr, nbr, path + [nbr], ntr, nti))
    return None


def solve_scenario(
    scenario: Dict[str, Any],
    route_stops: List[Dict[str, Any]],
    stop_times: List[Dict[str, Any]],
    trips: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    scenario: dict {origin, destinations, ordered, return_to_origin, goal, walk_edges}
    Returns dict with itinerary and costs, exploring permutations if ordered==false
    """
    origin: str = str(scenario["origin"])
    dests: List[str] = [str(x) for x in scenario["destinations"]]
    ordered: bool = bool(scenario.get("ordered", False))
    ret: bool = bool(scenario.get("return_to_origin", False))
    goal: str = str(scenario.get("goal", "least-time"))
    walk_edges: List[Dict[str, Any]] = list(scenario.get("walk_edges", []))

    adj: Dict[Node, List[Edge]]
    waits: Dict[str, int]
    travel: Dict[Tuple[str, str, str], int]
    adj, waits, travel = build_expanded_graph(route_stops, stop_times, trips, walk_edges)

    def nodes_at(stop: str) -> List[Node]:
        return [n for n in adj.keys() if n.startswith(stop + "__")]

    dest_perms: List[Tuple[str, ...]]
    if ordered:
        dest_perms = [tuple(dests)]
    else:
        dest_perms = list(itertools.permutations(dests))
    best: Tuple[int, int] | None = None
    best_perm: Tuple[str, ...] | None = None
    best_legs: List[Dict[str, Any]] | None = None
    best_full: List[Node] = []
    for perm in dest_perms:
        seq: List[str] = [origin] + list(perm)
        if ret:
            seq.append(origin)
        total_time = 0
        total_transfers = 0
        legs: List[Dict[str, Any]] = []
        feasible = True
        full_path: List[Node] = []
        chain_start_nodes: List[Node] | None = None
        for a, b in zip(seq, seq[1:]):
            starts: List[Node]
            if chain_start_nodes is None:
                starts = nodes_at(a)
            else:
                starts = chain_start_nodes
            if not starts:
                feasible = False
                break
            r: Tuple[int, int, List[Node]] | None = dijkstra(adj, starts, b, goal_mode=goal)
            if r is None:
                feasible = False
                break
            ti, tr, path = r
            total_time += ti
            total_transfers += tr
            legs.append({"from": a, "to": b, "time": ti, "transfers": tr, "path": path})
            if not full_path:
                full_path = list(path)
            else:
                full_path.extend(path[1:])
            chain_start_nodes = [path[-1]]
        if not feasible:
            continue
        cost: Tuple[int, int] = (
            (total_transfers, total_time)
            if goal == "least-transfer"
            else (total_time, total_transfers)
        )
        if best is None or cost < best:
            best = cost
            best_perm = perm
            best_legs = legs
            best_full = full_path

    if best is None or best_perm is None or best_legs is None:
        return {
            "error": "no feasible route",
            "scenario": str(scenario["name"]) if "name" in scenario else "unknown",
        }

    perm_list: List[str] = list(best_perm)
    return {
        "scenario": str(scenario.get("name", "unknown")),
        "origin": origin,
        "destinations_ordered": perm_list,
        "return_to_origin": ret,
        "goal": goal,
        "total_time": best[1] if goal == "least-transfer" else best[0],
        "total_transfers": best[0] if goal == "least-transfer" else best[1],
        "legs": best_legs,
        "full_path": best_full,
        "cost_tuple": best,
    }
