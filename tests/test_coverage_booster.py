import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import build
import patch_bfull
import publish
import publish_scenarios
import quality


def test_build_main_generates():
    # Exercise full build pipeline via direct call (covers 150+ stmts)
    build.main(check=False)
    # Verify outputs
    assert pathlib.Path("data/json/routes.json").exists()
    assert pathlib.Path("data/json/build_meta.json").exists()
    assert pathlib.Path("data/geo/routes.geojson").exists()
    # Also test check mode
    build.main(check=True)


def test_build_helpers_edge_cases():
    # Test error branches
    try:
        build.parse_bool("invalid_bool_value_xyz")
        assert False
    except build.ValidationError:
        pass
    # time_to_min invalid
    try:
        build.time_to_min("99:99")
        assert False
    except build.ValidationError:
        pass
    # validate_unique missing key
    try:
        build.validate_unique([{"route_id": ""}], "route_id", "routes.csv")
        assert False
    except build.ValidationError:
        pass
    # load_csv missing file
    try:
        build.load_csv(pathlib.Path("nonexistent.csv"))
        assert False
    except build.ValidationError:
        pass


def test_publish_full():
    # Exercise publish logic directly (not subprocess) for coverage
    assert isinstance(publish.is_dist_stale(), bool)
    # Dry run logic via main would be via subprocess, but test publish function
    # Ensure publish doesn't raise
    publish.publish()
    assert (pathlib.Path("dist/api/index.json")).exists()
    assert (pathlib.Path("dist/index.html")).exists()
    # Check again
    publish.main  # ensure function exists


def test_publish_scenarios_full():
    # Exercise scenario publish directly
    assert isinstance(publish_scenarios.is_stale(), bool)
    publish_scenarios.publish()
    assert pathlib.Path("dist/scenarios/index.json").exists()


def test_patch_and_quality_direct():
    # Patch helpers
    assert patch_bfull.time_to_min("02:15") == 135
    assert patch_bfull.min_to_time(135) == "02:15"
    # Quality main already tested elsewhere, but call again for coverage
    quality.main()
    # Ensure profiles accessible
    assert len(patch_bfull.PROFILES) == 8
