#!/usr/bin/env python3
"""
Publish scenarios - depends on dataset snapshot, no force dataset build.

- Uses snapshot from last dataset publish: dist/api (committed) or data/json if present.
- Validates scenarios/*.yaml, solves via route pure core, writes dist/scenarios/<name>.json
- Generates dist/scenarios/index.json manifest
- Updates dist/index.html to list both api and scenarios
- --check: fail if dist/scenarios stale vs scenarios/*.yaml
- --dry-run: preview
"""

import argparse
import json
import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCEN_DIR = ROOT / "scenarios"
DIST_API = ROOT / "dist" / "api"
DIST_SCEN = ROOT / "dist" / "scenarios"
JSON_DIR = ROOT / "data" / "json"


def ensure_data_json_from_snapshot():
    """If data/json missing (gitignored after checkout), restore from dist/api snapshot"""
    if JSON_DIR.exists() and any(JSON_DIR.glob("*.json")):
        return
    if DIST_API.exists() and any(DIST_API.glob("*.json")):
        JSON_DIR.mkdir(parents=True, exist_ok=True)
        for p in DIST_API.glob("*.json"):
            if p.name == "index.json":
                continue
            # copy api json back to data/json for route solving (preserve build_meta, etc)
            # dist/api has build_meta, halte_index etc. which correspond to data/json
            shutil.copy2(p, JSON_DIR / p.name)
        # geo not needed for scenarios but ensure
        geo_src = DIST_API / "routes.geojson"
        if geo_src.exists():
            (ROOT / "data" / "geo").mkdir(parents=True, exist_ok=True)
            shutil.copy2(geo_src, ROOT / "data" / "geo" / "routes.geojson")
        print(f"restored data/json from snapshot {DIST_API} -> {JSON_DIR}")
    else:
        print("no dataset snapshot found (dist/api or data/json missing)", file=sys.stderr)
        sys.exit(1)


def is_stale():
    if not DIST_SCEN.exists():
        return True
    scen_files = list(SCEN_DIR.glob("*.yaml"))
    if not scen_files:
        return False
    scen_mtime = max(p.stat().st_mtime for p in scen_files)
    dist_files = list(DIST_SCEN.glob("*"))
    if not dist_files:
        return True
    dist_mtime = max(p.stat().st_mtime for p in dist_files)
    return scen_mtime > dist_mtime


def publish():
    ensure_data_json_from_snapshot()
    # ensure api dist exists (snapshot)
    if not DIST_API.exists():
        print("dist/api missing - dataset publish required first", file=sys.stderr)
        sys.exit(1)

    DIST_SCEN.mkdir(parents=True, exist_ok=True)

    # load data for solving
    import route

    route_stops = json.load(open(JSON_DIR / "route_stops.json"))
    stop_times = json.load(open(JSON_DIR / "stop_times.json"))
    trips = json.load(open(JSON_DIR / "trips.json"))

    # helper to load yaml
    def load_yaml(path):
        try:
            import yaml

            return yaml.safe_load(open(path, encoding="utf-8"))
        except Exception:
            # fallback simple parser from bsd.py
            import re

            text = open(path, encoding="utf-8").read()
            data = {}
            # very minimal - use bsd.py's parser if available
            # fallback: try to import bsd
            try:
                sys.path.insert(0, str(ROOT / "scripts"))
                import bsd

                return bsd.load_scenario(str(path))
            except Exception:
                pass
            # simple
            lines = text.splitlines()
            for line in lines:
                m = re.match(r"^(\w+):\s*(.*)", line.strip())
                if m:
                    k, v = m.group(1), m.group(2).strip()
                    if k == "destinations" and v.startswith("["):
                        data[k] = [x.strip() for x in v[1:-1].split(",") if x.strip()]
                    elif v.lower() in ("true", "false"):
                        data[k] = v.lower() == "true"
                    else:
                        data[k] = v
            data["walk_edges"] = data.get("walk_edges", [])
            return data

    count = 0
    for yaml_path in sorted(SCEN_DIR.glob("*.yaml")):
        if yaml_path.name == "schema.yaml":
            continue
        scen = load_yaml(yaml_path)
        if not scen or "origin" not in scen:
            print(f"skip invalid {yaml_path.name}")
            continue
        # validate
        res = route.solve_scenario(scen, route_stops, stop_times, trips)
        out_path = DIST_SCEN / f"{yaml_path.stem}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2, ensure_ascii=False)
        # copy yaml as well for reference
        shutil.copy2(yaml_path, DIST_SCEN / yaml_path.name)
        count += 1
        print(
            f"solved {yaml_path.name} -> {out_path.name} transfers={res.get('total_transfers')} time={res.get('total_time')}"
        )

    # index
    manifest = {
        "name": "BSD Link Scenarios",
        "generated_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "counts": {"scenarios": count},
        "scenarios": [p.stem for p in sorted(SCEN_DIR.glob("*.yaml")) if p.name != "schema.yaml"],
        "endpoints": [p.name for p in sorted(DIST_SCEN.glob("*"))],
    }
    with open(DIST_SCEN / "index.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    # update root index.html to include scenarios (preserve api index.html logic from publish.py)
    dist_root = ROOT / "dist"
    scen_exists = (dist_root / "scenarios" / "index.json").exists()
    scen_li = (
        '<li><a href="scenarios/index.json">scenarios/index.json</a> - scenario results</li>'
        if scen_exists
        else ""
    )
    scen_p = (
        "<p>Scenarios: <code>/scenarios/intermoda-*.json</code> + <code>.yaml</code></p>"
        if scen_exists
        else ""
    )
    html = f"""<!doctype html><meta charset=utf-8><title>BSD Link</title>
<h1>BSD Link</h1>
<p>Dataset + Scenarios</p>
<ul>
<li><a href="api/index.json">api/index.json</a> - API manifest</li>
<li><a href="api/routes.geojson">api/routes.geojson</a> - 41 Points + 9 LineStrings</li>
{scen_li}
</ul>
<p>API: <code>/api/routes.json</code> <code>/api/stops.json</code> <code>/api/halte_index.json</code></p>
{scen_p}
<p>Dataset via <code>python scripts/build.py</code>, scenarios via <code>route.solve_scenario</code></p>
"""
    (dist_root / "index.html").write_text(html, encoding="utf-8")
    (dist_root / ".nojekyll").touch(exist_ok=True)
    print(f"publish_scenarios ok: {count} scenarios -> {DIST_SCEN}, index.html updated")


def main():
    ap = argparse.ArgumentParser(description="Publish scenarios snapshot")
    ap.add_argument("--check", action="store_true", help="fail if stale")
    ap.add_argument("--dry-run", action="store_true", help="preview")
    args = ap.parse_args()
    if args.check:
        if is_stale():
            print("dist/scenarios stale", file=sys.stderr)
            sys.exit(1)
        print("dist/scenarios fresh")
        return
    if args.dry_run:
        print(f"would publish {len(list(SCEN_DIR.glob('*.yaml')))} scenarios -> {DIST_SCEN}")
        return
    publish()


if __name__ == "__main__":
    main()
