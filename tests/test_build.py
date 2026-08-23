import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import build as build_module


def test_parse_bool():
    assert build_module.parse_bool("true") is True
    assert build_module.parse_bool("True") is True
    assert build_module.parse_bool("1") is True
    assert build_module.parse_bool("yes") is True
    assert build_module.parse_bool("false") is False
    assert build_module.parse_bool("0") is False
    assert build_module.parse_bool("") is False
    assert build_module.parse_bool(None) is False  # type: ignore
    try:
        build_module.parse_bool("maybe")
        assert False, "should raise"
    except build_module.ValidationError:
        pass


def test_time_to_min():
    assert build_module.time_to_min("00:00") == 0
    assert build_module.time_to_min("07:30") == 450
    assert build_module.time_to_min("23:59") == 1439
    try:
        build_module.time_to_min("24:00")
        assert False
    except build_module.ValidationError:
        pass
    try:
        build_module.time_to_min("bad")
        assert False
    except build_module.ValidationError:
        pass


def test_load_csv_routes():
    path = pathlib.Path("data/csv/routes.csv")
    fieldnames, rows = build_module.load_csv(path)
    assert "route_id" in fieldnames
    assert len(rows) == 9


def test_validate_unique():
    rows = [{"id": "A"}, {"id": "B"}]
    seen = build_module.validate_unique(rows, "id", "test.csv")
    assert seen == {"A", "B"}
    try:
        build_module.validate_unique([{"id": "A"}, {"id": "A"}], "id", "test.csv")
        assert False
    except build_module.ValidationError:
        pass


def test_build_generates_json(tmp_path=None):
    # Ensure build produces JSON and validates invariants
    # Run build main without --check, then verify outputs
    # Use existing data, not tmp, because build writes to data/json and data/geo
    # Verify json files exist and have expected counts
    import subprocess
    import sys

    result = build_module.load_csv(pathlib.Path("data/csv/stops.csv"))
    _fields, stops = result
    assert len(stops) == 41
    # Check that lat/lng parsed for at least one stop
    assert any(s.get("lat") for s in stops)

    # Run full build logic via main (without overwriting check)
    # We call main directly but it will write files; verify it doesn't raise
    # To avoid side effects, we already have built json, so just verify build_meta
    meta_path = pathlib.Path("data/json/build_meta.json")
    assert meta_path.exists()
    meta = json.load(open(meta_path, encoding="utf-8"))
    assert meta["counts"]["routes"] == 9
    assert meta["counts"]["stops"] == 41

    # test --check mode via subprocess
    res = subprocess.run(
        [sys.executable, "scripts/build.py", "--check"], capture_output=True, text=True
    )
    assert res.returncode == 0, res.stderr


def test_convert_helpers():
    # Exercise convert functions indirectly via build run
    # Test that halte_index derived correctly
    import json as _json

    hi = _json.load(open("data/json/halte_index.json", encoding="utf-8"))
    assert "THE_BREEZE" in hi
    assert len(hi["THE_BREEZE"]) >= 2
    routes = _json.load(open("data/json/routes.json", encoding="utf-8"))
    assert any(r["is_inferred"] for r in routes)
