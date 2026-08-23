import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import bsd as bsd_module


def test_load_data():
    rs, st, tr, hi, routes, stops = bsd_module.load_data()
    assert len(rs) == 95
    assert len(stops) == 41
    assert len(routes) == 9
    assert "THE_BREEZE" in hi


def test_parse_yaml_simple():
    txt = """
name: test-scenario
origin: PASAR_MODERN
destinations: [ICON, AEON_MALL_2]
ordered: false
return_to_origin: true
goal: least-transfer
walk_edges: []
"""
    data = bsd_module.parse_yaml_simple(txt)
    assert data["origin"] == "PASAR_MODERN"
    assert data["destinations"] == ["ICON", "AEON_MALL_2"]
    assert data["ordered"] is False
    assert data["return_to_origin"] is True
    assert data["walk_edges"] == []


def test_parse_yaml_simple_with_walk():
    txt = """
origin: PASAR_MODERN
destinations: [THE_BREEZE]
walk_edges:
  - from: AEON_MALL_2
    to: THE_BREEZE
    minutes: 8
    note: test walk
"""
    data = bsd_module.parse_yaml_simple(txt)
    assert len(data["walk_edges"]) == 1
    assert data["walk_edges"][0]["from"] == "AEON_MALL_2"
    assert data["walk_edges"][0]["minutes"] == 8


def test_load_scenario_yaml_path():
    scen = bsd_module.load_scenario("scenarios/intermoda-aeon-breeze-icon-least-transfer.yaml")
    assert scen["origin"] == "PASAR_MODERN"
    assert "destinations" in scen
    assert scen["goal"] == "least-transfer"


def test_bsd_cli_halte():
    res = subprocess.run(
        [sys.executable, "scripts/bsd.py", "--halte", "THE_BREEZE"], capture_output=True, text=True
    )
    assert res.returncode == 0
    assert "THE_BREEZE" in res.stdout
    assert "routes" in res.stdout.lower()


def test_bsd_cli_next():
    res = subprocess.run(
        [sys.executable, "scripts/bsd.py", "--next", "PASAR_MODERN", "--time", "07:00"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    assert "PASAR_MODERN" in res.stdout


def test_bsd_cli_scenario():
    res = subprocess.run(
        [
            sys.executable,
            "scripts/bsd.py",
            "--scenario",
            "scenarios/intermoda-aeon-breeze-icon-least-transfer.yaml",
        ],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    assert "total_time" in res.stdout or "Summary" in res.stdout


def test_bsd_cli_list_routes():
    res = subprocess.run(
        [sys.executable, "scripts/bsd.py", "--list-routes"], capture_output=True, text=True
    )
    assert res.returncode == 0
    assert "INT_SEKT13" in res.stdout


def test_bsd_cli_list_stops():
    res = subprocess.run(
        [sys.executable, "scripts/bsd.py", "--list-stops"], capture_output=True, text=True
    )
    assert res.returncode == 0
    assert "PASAR_MODERN" in res.stdout
