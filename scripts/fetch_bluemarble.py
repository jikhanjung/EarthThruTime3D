#!/usr/bin/env python3
"""Fetch the NASA Blue Marble present-day satellite base (jikhanjung P10 §3.1).

Usage: .venv/bin/python scripts/fetch_bluemarble.py [--verify-only]

One WMS GetMap per size from NASA EOSDIS GIBS (`BlueMarble_ShadedRelief_Bathymetry`, EPSG:4326,
the default base of GSM's whole-Earth view), kept under data/sources/bluemarble/ and
published into data/derived/present-earth/ (section `base`: 8192x4096 and 4096x2048
equirectangular JPEGs, longitude from -180, latitude 90 -> -90).
sources/bluemarble.json pins bytes and SHA-256; a later run must reproduce them or fail.
The visitor's browser never asks GIBS: the server ships these files.
"""
import argparse
import hashlib
import json
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

import present_catalogue

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/sources/bluemarble"
MANIFEST = ROOT / "sources/bluemarble.json"
WMS = "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi"
LAYER = "BlueMarble_ShadedRelief_Bathymetry"
SIZES = (8192, 4096)
#: An error page or a blank tile is far smaller than the world at these sizes
MIN_BYTES = {8192: 2_000_000, 4096: 500_000}


def url_for(width):
    query = {"SERVICE": "WMS", "REQUEST": "GetMap", "VERSION": "1.3.0", "LAYERS": LAYER, "STYLES": "",
             "CRS": "EPSG:4326", "BBOX": "-90,-180,90,180", "WIDTH": width, "HEIGHT": width // 2,
             "FORMAT": "image/jpeg"}
    return f"{WMS}?{urllib.parse.urlencode(query)}"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args(argv)
    pinned = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else None
    OUT.mkdir(parents=True, exist_ok=True)
    files = {}
    for width in SIZES:
        path = OUT / f"{width}.jpg"
        if args.verify_only:
            blob = path.read_bytes()
        else:
            request = urllib.request.Request(url_for(width), headers={"User-Agent": "EarthThruTime3D/1.0"})
            with urllib.request.urlopen(request, timeout=300) as response:
                if response.headers.get_content_type() != "image/jpeg":
                    raise SystemExit(f"{width}: GIBS sent {response.headers.get_content_type()}")
                blob = response.read()
            if len(blob) < MIN_BYTES[width]:
                raise SystemExit(f"{width}: only {len(blob)} bytes")
        entry = {"path": f"{width}.jpg", "url": url_for(width), "width": width, "height": width // 2,
                 "bytes": len(blob), "sha256": hashlib.sha256(blob).hexdigest()}
        if pinned:
            old = next((f for f in pinned["files"] if f["width"] == width), None)
            if old and (old["bytes"], old["sha256"]) != (entry["bytes"], entry["sha256"]):
                raise SystemExit(f"{width}: differs from the pinned manifest; update it deliberately")
        if not args.verify_only:
            path.write_bytes(blob)
        files[width] = entry
    if not pinned:
        MANIFEST.write_text(json.dumps({
            "id": "bluemarble-gibs", "layer": LAYER, "service": WMS,
            "license": "NASA imagery, no copyright (credit requested)",
            "citation": "NASA Earth Observatory Blue Marble (shaded relief and bathymetry), served by NASA EOSDIS GIBS.",
            "imagery_epoch": "2004 composite",
            "retrieved": date.today().isoformat(),
            "files": list(files.values()),
        }, indent=1) + "\n")
    pinned = json.loads(MANIFEST.read_text())
    present_catalogue.write_section("base", {str(w): ((OUT / f"{w}.jpg").read_bytes(), "jpg") for w in SIZES}, {
        "layer": LAYER, "citation": pinned["citation"], "imagery_epoch": pinned["imagery_epoch"]})
    print("ok", {w: f["bytes"] for w, f in files.items()})


if __name__ == "__main__":
    main()
