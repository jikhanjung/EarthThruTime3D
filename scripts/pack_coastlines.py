#!/usr/bin/env python3
"""Pack the PaleoCoastlines v7.1 coastlines (Kocsis & Scotese 2021) for the viewer.

The coastline polygons are already in reconstructed coordinates and share the PALEOMAP
frame with the 2016 PaleoAtlas masks (devlog 026), so they are drawn over the masks as
they are, with no rotation. Each age becomes one small JSON file of rings in longitude
and latitude, simplified to 0.1 degree, plus an index the page reads.

These coastlines are the PaleoDEM coastlines moved to the maximum transgression that
marine fossils in the Paleobiology Database indicate, so they are a second, fossil-checked
line beside the mask's edge rather than the same line redrawn.
"""
import argparse
import hashlib
import json
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pack_plates import shapefile_rings, simplify  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "sources/paleogeography/paleocoastlines2021.json"
OUT = ROOT / "data/derived/paleocoastlines"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tolerance", type=float, default=0.1)
    parser.add_argument("--min-points", type=int, default=4)
    args = parser.parse_args()

    manifest = json.loads(MANIFEST.read_text())
    archive = ROOT / manifest["archive"]["path"]
    data = archive.read_bytes()
    if (len(data) != manifest["archive"]["bytes"]
            or hashlib.sha256(data).hexdigest() != manifest["archive"]["sha256"]):
        raise SystemExit(f"{archive} differs from {MANIFEST.relative_to(ROOT)}")

    OUT.mkdir(parents=True, exist_ok=True)
    for stale in OUT.glob("coastlines-*.json"):
        stale.unlink()
    ages = []
    with zipfile.ZipFile(archive) as bundle, tempfile.TemporaryDirectory() as tmp:
        bundle.extractall(tmp, members=[name for name in bundle.namelist() if name.startswith("Data/CS/")])
        for shp in Path(tmp, "Data/CS").glob("*Ma_CS_v7.shp"):
            age = float(shp.name.split("Ma_")[0])
            rings = []
            for record in shapefile_rings(shp):
                for ring in record:
                    points = simplify(ring, args.tolerance)
                    if len(points) >= args.min_points:
                        rings.append([round(value, 2) for point in points for value in point])
            name = f"coastlines-{int(age):03d}.json"
            (OUT / name).write_text(json.dumps({"age_ma": age, "rings": rings}, separators=(",", ":")))
            ages.append({"age_ma": age, "file": name, "rings": len(rings),
                         "points": sum(len(ring) // 2 for ring in rings)})
    ages.sort(key=lambda entry: entry["age_ma"])
    index = {"schema_version": 1, "dataset": manifest["id"], "title": manifest["title"],
             "citation": manifest["citation"], "license": manifest["license"]["name"],
             "license_url": manifest["license"]["url"], "evidence": manifest["evidence"],
             "tolerance_deg": args.tolerance, "ages": ages}
    (OUT / "index.json").write_text(json.dumps(index, indent=1, ensure_ascii=False) + "\n")
    total = sum((OUT / entry["file"]).stat().st_size for entry in ages)
    print(f"{OUT.relative_to(ROOT)}: {len(ages)} ages {ages[0]['age_ma']:g}-{ages[-1]['age_ma']:g} Ma, "
          f"{sum(entry['points'] for entry in ages)} points, {total / 1024:.0f} KiB")


if __name__ == "__main__":
    main()
