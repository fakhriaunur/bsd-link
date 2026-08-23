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
import itertools
import heapq
from collections import defaultdict
from typing import Dict, List, Tuple, Set

Node = str
Edge = Tuple[Node, int, int, str]  # neighbor, time, transfers, label

def time_to_min(t: str) -> int:
    h, m = map(int, t.split(":"))
    return h*60+m

def build_travel_times(route_stops, stop_times):
    """
    Avg travel minutes per consecutive pair per route.
    route_stops: list of {route_id, stop_id, seq}
    stop_times: list of {trip_id, stop_id, arrival_time, stop_seq}
    Returns dict (route_id, from_stop, to_stop) -> avg_min
    """
    # map trip_id -> route_id via trips? But we have stop_times only, need trip->route via trips input alternative.
    # Instead compute via grouping stop_times by trip_id and sorting by stop_seq.
    # For each trip sorted, consecutive pairs give delta.
    by_trip = defaultdict(list)
    for st in stop_times:
        by_trip[st["trip_id"]].append(st)
    # need trip->route lookup passed separately, but we can infer route via route_stops membership per pair?
    # Simpler: compute delta per pair regardless of route, then assign to route that contains both stops consecutively.
    # Build route consecutive pairs set
    route_pairs = set()
    by_route = defaultdict(list)
    for rs in route_stops:
        by_route[rs["route_id"]].append(rs)
    for rid, rss in by_route.items():
        rss_sorted = sorted(rss, key=lambda x: x["seq"])
        for a, b in zip(rss_sorted, rss_sorted[1:]):
            route_pairs.add((rid, a["stop_id"], b["stop_id"]))

    deltas = defaultdict(list)
    for trip_id, sts in by_trip.items():
        # need to know route for this trip - infer via first stop's route? Instead we match pair to any route containing both consecutively.
        # Sort by stop_seq
        sts_sorted = sorted(sts, key=lambda x: x["stop_seq"])
        for a, b in zip(sts_sorted, sts_sorted[1:]):
            # find routes where a and b are consecutive
            for rid in set(r["route_id"] for r in route_stops if r["stop_id"] in (a["stop_id"], b["stop_id"])):
                if (rid, a["stop_id"], b["stop_id"]) in route_pairs:
                    delta = time_to_min(b["arrival_time"]) - time_to_min(a["arrival_time"])
                    if delta >=0:
                        deltas[(rid, a["stop_id"], b["stop_id"])].append(delta)
    # avg
    avg = {}
    for k, lst in deltas.items():
        avg[k] = sum(lst)//len(lst) if lst else 2
    # fallback 2min for pairs with no data (e.g., inferred)
    for rp in route_pairs:
        if rp not in avg:
            avg[rp] = 2
    return avg

def compute_headway_wait(trips):
    """
    per route avg headway/2 wait minutes. trips: list {route_id, departure_time}
    Returns dict route_id -> wait_min
    """
    by_route = defaultdict(list)
    for t in trips:
        by_route[t["route_id"]].append(time_to_min(t["departure_time"]))
    waits = {}
    for rid, times in by_route.items():
        times = sorted(times)
        if len(times) < 2:
            waits[rid] = 15
            continue
        diffs = [b-a for a,b in zip(times, times[1:]) if b>a]
        # filter negative wrap (next day not needed)
        avg_headway = sum(diffs)//len(diffs) if diffs else 30
        waits[rid] = max(5, avg_headway//2)
    return waits

def build_expanded_graph(route_stops, stop_times, trips, walk_edges=None):
    """
    Returns adjacency dict Node -> list[Edge]
    walk_edges: list {from, to, minutes}
    """
    if walk_edges is None:
        walk_edges = []
    travel = build_travel_times(route_stops, stop_times)
    waits = compute_headway_wait(trips)

    # nodes
    nodes: Set[Node] = set()
    by_stop = defaultdict(list)
    for rs in route_stops:
        nid = f"{rs['stop_id']}__{rs['route_id']}"
        nodes.add(nid)
        by_stop[rs["stop_id"]].append(nid)

    adj: Dict[Node, List[Edge]] = {n: [] for n in nodes}

    # route edges
    by_route = defaultdict(list)
    for rs in route_stops:
        by_route[rs["route_id"]].append(rs)
    for rid, rss in by_route.items():
        rss_sorted = sorted(rss, key=lambda x: x["seq"])
        for a, b in zip(rss_sorted, rss_sorted[1:]):
            u = f"{a['stop_id']}__{rid}"
            v = f"{b['stop_id']}__{rid}"
            t = travel.get((rid, a["stop_id"], b["stop_id"]), 2)
            adj[u].append((v, t, 0, rid))

    # transfer edges: fully connect per stop across routes
    for stop_id, nids in by_stop.items():
        if len(nids) < 2:
            continue
        for u in nids:
            _, ru = u.rsplit("__",1)
            for v in nids:
                if u == v:
                    continue
                _, rv = v.rsplit("__",1)
                # wait cost = avg wait of target route
                w = waits.get(rv, 15)
                adj[u].append((v, w, 1, f"transfer:{ru}->{rv}"))

    # walk edges: connect any node at from_stop to any node at to_stop
    for w in walk_edges:
        f = w["from"]
        t = w["to"]
        mins = int(w["minutes"])
        for u in by_stop.get(f, []):
            for v in by_stop.get(t, []):
                if u == v:
                    continue
                # walk not counted as transfer, but time = mins
                adj[u].append((v, mins, 0, f"walk:{f}->{t}"))
                # bidirectional if not already defined both ways via two entries? Add reverse if undirected.
        # also reverse if walk is considered bidirectional, caller should provide both directions entries
    return adj, waits, travel

def dijkstra(adj, start_nodes, goal_stop, goal_mode="least-time"):
    """
    goal_stop: stop_id to reach (any route)
    goal_mode: least-transfer (primary transfers), least-time (primary time)
    Returns (total_time, transfers, path_nodes) or None
    """
    # priority queue: (primary, secondary, node, path, transfers, time)
    pq = []
    best = {}
    # init
    for s in start_nodes:
        if goal_mode == "least-transfer":
            heapq.heappush(pq, (0, 0, s, [s], 0, 0))
        else:
            heapq.heappush(pq, (0, 0, s, [s], 0, 0))

    visited = set()
    while pq:
        if goal_mode == "least-transfer":
            transfers, time, node, path, tr, ti = heapq.heappop(pq)
            primary, secondary = transfers, time
        else:
            time, transfers, node, path, tr, ti = heapq.heappop(pq)
            primary, secondary = time, transfers

        # goal check: node stop part matches
        stop_part = node.rsplit("__",1)[0]
        if stop_part == goal_stop:
            return ti, tr, path

        if node in visited:
            continue
        visited.add(node)

        for nbr, wt, wf, label in adj.get(node, []):
            if nbr in visited:
                continue
            nti = ti + wt
            ntr = tr + wf
            if nbr in best and best[nbr][0] <= ntr and best[nbr][1] <= nti:
                # dominated
                pass
            best[nbr] = (ntr, nti)
            if goal_mode == "least-transfer":
                heapq.heappush(pq, (ntr, nti, nbr, path+[nbr], ntr, nti))
            else:
                heapq.heappush(pq, (nti, ntr, nbr, path+[nbr], ntr, nti))
    return None

def solve_scenario(scenario, route_stops, stop_times, trips):
    """
    scenario: dict {origin, destinations, ordered, return_to_origin, goal, walk_edges}
    Returns dict with itinerary and costs, exploring permutations if ordered==false
    """
    origin = scenario["origin"]
    dests = scenario["destinations"]
    ordered = scenario.get("ordered", False)
    ret = scenario.get("return_to_origin", False)
    goal = scenario.get("goal", "least-time")
    walk_edges = scenario.get("walk_edges", [])

    adj, waits, travel = build_expanded_graph(route_stops, stop_times, trips, walk_edges)

    # helper to get start nodes for a stop
    def nodes_at(stop):
        return [n for n in adj.keys() if n.startswith(stop+"__")]
    # helper shortest between stops
    def shortest(a_stop, b_stop):
        starts = nodes_at(a_stop)
        if not starts:
            return None
        res = dijkstra(adj, starts, b_stop, goal_mode=goal)
        return res

    # permutations
    dest_perms = [dests] if ordered else list(itertools.permutations(dests))
    best = None
    best_perm = None
    best_legs = None
    for perm in dest_perms:
        seq = [origin] + list(perm)
        if ret:
            seq.append(origin)
        total_time = 0
        total_transfers = 0
        legs = []
        feasible = True
        full_path = []
        for a,b in zip(seq, seq[1:]):
            r = shortest(a,b)
            if r is None:
                feasible=False
                break
            ti,tr,path = r
            total_time += ti
            total_transfers += tr
            legs.append({"from":a,"to":b,"time":ti,"transfers":tr,"path":path})
            # accumulate full_path with dedup
            if not full_path:
                full_path = path
            else:
                full_path.extend(path[1:])
        if not feasible:
            continue
        # choose best by goal
        cost = (total_transfers, total_time) if goal=="least-transfer" else (total_time, total_transfers)
        if best is None or cost < best:
            best = cost
            best_perm = perm
            best_legs = legs
            best_full = full_path

    if best is None:
        return {"error": "no feasible route", "scenario": scenario["name"] if "name" in scenario else "unknown"}

    return {
        "scenario": scenario.get("name","unknown"),
        "origin": origin,
        "destinations_ordered": list(best_perm),
        "return_to_origin": ret,
        "goal": goal,
        "total_time": best[1] if goal=="least-transfer" else best[0],
        "total_transfers": best[0] if goal=="least-transfer" else best[1],
        "legs": best_legs,
        "full_path": best_full,
        "cost_tuple": best,
    }
