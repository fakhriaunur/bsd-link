#!/usr/bin/env python3
"""
Publish static JSON API - thin shell over build.

- validates via build.py
- copies data/json -> dist/api (or public/api) for local preview
- generates dist/api/index.json manifest
- --check: fail if dist stale vs data/csv
- --dry-run: print what would publish, no write

No deps, stdlib only.
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_DIR = ROOT / "data" / "csv"
JSON_DIR = ROOT / "data" / "json"
DIST_DIR = ROOT / "dist" / "api"


def run_build():
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build.py")], capture_output=True, text=True
    )
    if r.returncode != 0:
        print(r.stdout)
        print(r.stderr, file=sys.stderr)
        sys.exit(r.returncode)
    print(r.stdout.strip())


def is_dist_stale():
    if not DIST_DIR.exists():
        return True
    json_mtime = max((p.stat().st_mtime for p in JSON_DIR.glob("*.json")), default=0)
    dist_mtime = max((p.stat().st_mtime for p in DIST_DIR.glob("*.json")), default=0)
    if not list(DIST_DIR.glob("*.json")):
        return True
    csv_mtime = max((p.stat().st_mtime for p in CSV_DIR.glob("*.csv")), default=0)
    return csv_mtime > json_mtime or json_mtime > dist_mtime


def publish():
    run_build()
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    # copy jsons
    for p in JSON_DIR.glob("*.json"):
        shutil.copy2(p, DIST_DIR / p.name)
    # also copy geo
    geo_src = ROOT / "data" / "geo" / "routes.geojson"
    if geo_src.exists():
        shutil.copy2(geo_src, DIST_DIR / "routes.geojson")
    # manifest
    meta = json.load(open(JSON_DIR / "build_meta.json"))
    manifest = {
        "name": "BSD Link API",
        "version": "v1",
        "generated_at": meta.get("generated_at"),
        "counts": meta.get("counts"),
        "endpoints": [p.name for p in sorted(DIST_DIR.glob("*.json"))]
        + (["routes.geojson"] if (DIST_DIR / "routes.geojson").exists() else []),
        "usage": {
            "routes": "/api/routes.json",
            "stops": "/api/stops.json",
            "halte_index": "/api/halte_index.json",
            "route_stops": "/api/route_stops.json",
            "trips": "/api/trips.json",
            "stop_times": "/api/stop_times.json",
        },
    }
    with open(DIST_DIR / "index.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    # fix Pages 404: root needs index.html + .nojekyll
    dist_root = ROOT / "dist"
    scenarios_exist = (dist_root / "scenarios").exists() and any(
        (dist_root / "scenarios").glob("*")
    )
    scen_li = (
        '<li><a href="scenarios/index.json">scenarios/index.json</a> - scenarios results</li>'
        if scenarios_exist
        else ""
    )
    scen_p = "<p>Scenarios: <code>/scenarios/intermoda-*.json</code></p>" if scenarios_exist else ""
    html = f"""<!doctype html><meta charset=utf-8><title>BSD Link</title>
<h1>BSD Link</h1>
<p>Dataset + Scenarios</p>
<ul>
<li><a href="api/index.json">api/index.json</a> - {len(list(DIST_DIR.glob("*.json")))} files (routes, stops, halte_index)</li>
<li><a href="api/routes.geojson">api/routes.geojson</a> - 41 Points + 9 LineStrings</li>
{scen_li}
</ul>
<p>API: <code>/api/routes.json</code> <code>/api/stops.json</code> <code>/api/halte_index.json</code></p>
{scen_p}
<p>Generated {meta.get("generated_at")}</p>
"""
    (dist_root / "index.html").write_text(html, encoding="utf-8")
    (dist_root / ".nojekyll").touch(exist_ok=True)
    print(
        f"publish ok: {len(list(DIST_DIR.glob('*')))} files -> {DIST_DIR}, index.html + .nojekyll at {dist_root}"
    )


def main():
    ap = argparse.ArgumentParser(description="Publish BSD Link API")
    ap.add_argument("--check", action="store_true", help="fail if dist stale")
    ap.add_argument("--dry-run", action="store_true", help="print plan, no write")
    args = ap.parse_args()
    if args.check:
        if is_dist_stale():
            print("dist stale: run publish", file=sys.stderr)
            sys.exit(1)
        print("dist fresh")
        return
    if args.dry_run:
        print(f"would publish {len(list(JSON_DIR.glob('*.json')))} json + geo -> {DIST_DIR}")
        meta = (
            json.load(open(JSON_DIR / "build_meta.json"))
            if (JSON_DIR / "build_meta.json").exists()
            else {}
        )
        print(json.dumps(meta.get("counts", {}), indent=2))
        return
    publish()


if __name__ == "__main__":
    main()
