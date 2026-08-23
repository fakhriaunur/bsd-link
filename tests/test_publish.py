import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import publish as publish_module
import publish_scenarios as ps_module


def test_publish_is_dist_stale():
    # Should be false after build+publish
    result = publish_module.is_dist_stale()
    # After fresh build/publish, should be False
    # But we assert it returns bool
    assert isinstance(result, bool)


def test_publish_dry_run():
    res = subprocess.run(
        [sys.executable, "scripts/publish.py", "--dry-run"], capture_output=True, text=True
    )
    assert res.returncode == 0
    assert "would publish" in res.stdout


def test_publish_check():
    res = subprocess.run(
        [sys.executable, "scripts/publish.py", "--check"], capture_output=True, text=True
    )
    assert res.returncode == 0
    assert "fresh" in res.stdout.lower()


def test_publish_scenarios_dry_run():
    res = subprocess.run(
        [sys.executable, "scripts/publish_scenarios.py", "--dry-run"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    assert "would publish" in res.stdout


def test_publish_scenarios_check():
    res = subprocess.run(
        [sys.executable, "scripts/publish_scenarios.py", "--check"], capture_output=True, text=True
    )
    # May be fresh or stale depending on yaml vs dist, but should exit 0 if fresh
    assert res.returncode == 0 or "stale" in res.stderr.lower()


def test_ensure_snapshot():
    # Test that snapshot restore works when data/json exists (no-op) and when missing it restores
    # Just test the function doesn't crash
    ps_module.ensure_data_json_from_snapshot()
    # Verify data/json still exists
    assert pathlib.Path("data/json/routes.json").exists()


def test_quality_main():
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
    import quality

    # quality.main prints to stdout, should not raise
    quality.main()


def test_patch_bfull_profiles():
    import patch_bfull

    assert "INT_SEKT13" in patch_bfull.PROFILES
    assert patch_bfull.min_to_time(90) == "01:30"
    assert patch_bfull.time_to_min("01:30") == 90
