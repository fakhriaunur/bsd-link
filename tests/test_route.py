import json, pathlib

import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import route

JDIR = pathlib.Path("data/json")

def load_data():
    route_stops = json.load(open(JDIR/"route_stops.json"))
    stop_times = json.load(open(JDIR/"stop_times.json"))
    trips = json.load(open(JDIR/"trips.json"))
    return route_stops, stop_times, trips

def test_halte_index():
    hi = json.load(open(JDIR/"halte_index.json"))
    assert "THE_BREEZE" in hi
    assert len(hi["THE_BREEZE"]) >= 5
    assert "PASAR_MODERN" in hi

def test_graph_build():
    rs, st, tr = load_data()
    adj, waits, travel = route.build_expanded_graph(rs, st, tr, [])
    assert len(adj) == 95
    # at least one transfer edge at THE_BREEZE
    breeze_nodes = [n for n in adj if n.startswith("THE_BREEZE__")]
    assert len(breeze_nodes) >= 2
    # check route edge exists
    assert any("BREEZE_AEON_ICE" in str(e) for edges in adj.values() for e in edges)

def test_least_transfer_scenario():
    rs, st, tr = load_data()
    scenario = {
        "name": "intermoda-aeon-breeze-icon-least-transfer",
        "origin": "PASAR_MODERN",
        "destinations": ["ICON", "AEON_MALL_2", "THE_BREEZE"],
        "ordered": False,
        "return_to_origin": True,
        "goal": "least-transfer",
        "walk_edges": []
    }
    res = route.solve_scenario(scenario, rs, st, tr)
    assert "error" not in res
    # least-transfer should be 1 transfer (BLUE then YELLOW)
    assert res["total_transfers"] <= 2, f"got {res['total_transfers']}"
    assert res["total_time"] > 0
    # destinations_ordered should be ICON first due north monotonic
    # not strict, but check all destinations covered
    assert set(res["destinations_ordered"]) == {"ICON", "AEON_MALL_2", "THE_BREEZE"}

def test_least_time_with_walk():
    rs, st, tr = load_data()
    scenario = {
        "name": "walk",
        "origin": "PASAR_MODERN",
        "destinations": ["ICON", "AEON_MALL_2", "THE_BREEZE"],
        "ordered": False,
        "return_to_origin": True,
        "goal": "least-time",
        "walk_edges": [{"from":"AEON_MALL_2","to":"THE_BREEZE","minutes":8},{"from":"THE_BREEZE","to":"AEON_MALL_2","minutes":8}]
    }
    res = route.solve_scenario(scenario, rs, st, tr)
    assert "error" not in res
    assert res["total_time"] < 100  # heuristic with 2min hops + walks, should be <100 for loop

def test_monotone():
    st = json.load(open(JDIR/"stop_times.json"))
    from collections import defaultdict
    by_trip = defaultdict(list)
    for s in st:
        by_trip[s["trip_id"]].append(s)
    for tid, lst in by_trip.items():
        times = [route.time_to_min(x["arrival_time"]) for x in sorted(lst, key=lambda z: z["stop_seq"])]
        assert times == sorted(times), f"monotone fail {tid}"
