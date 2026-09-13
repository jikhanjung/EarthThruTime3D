#!/usr/bin/env python3
"""Pack Scotese's PALEOMAP plate model for measurement, straight from the atlas zip.

The PALEOMAP PaleoAtlas for GPlates (Scotese 2016, doi:10.5281/zenodo.10251792) ships a
rotation file and plate polygons beside the maps. They are packed in the same shape as
the EarthByte models so scripts/measure_longitude_offsets.py can compose them, but no
manifest is written under sources/plate-models/, so the viewer never offers this model.
The output lands in data/derived/plates/paleomap2016/, which is gitignored.
"""
import argparse
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pack_plates import OUT, features, rotations  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ZIP = ROOT / "docs/pdf/Scotese_PaleoAtlas_v3.zip"
MODEL = "paleomap2016"
ROTATION = "PALEOMAP Global Plate Model/PALEOMAP_PlateModel.rot"
POLYGONS = "PALEOMAP Global Plate Model/PALEOMAP_PlatePolygons.gpml"


def member(archive, suffix):
    names = [name for name in archive.namelist() if name.endswith(suffix)]
    if len(names) != 1:
        raise SystemExit(f"expected one {suffix} in the zip, found {len(names)}")
    return archive.read(names[0]).decode("utf-8", "replace")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zip", nargs="?", type=Path, default=DEFAULT_ZIP)
    parser.add_argument("--tolerance", type=float, default=0.12)
    parser.add_argument("--min-points", type=int, default=4)
    args = parser.parse_args()

    with zipfile.ZipFile(args.zip) as archive:
        rotation_text = member(archive, ROTATION)
        polygon_text = member(archive, POLYGONS)

    attribution = {"model": MODEL, "title": "PALEOMAP (Scotese 2016)",
                   "citation": "Scotese, C. R., 2016. PALEOMAP PaleoAtlas for GPlates and the "
                               "PaleoData Plotter Program. PALEOMAP Project. "
                               "doi:10.5281/zenodo.10251792",
                   "reference_frame": "PALEOMAP (plate 001 'Hot Spot to PMAG' is identity)",
                   "covers_ma": [0, 1100],
                   "use": "local measurement only; not served"}
    directory = OUT / MODEL
    directory.mkdir(parents=True, exist_ok=True)

    # About 200 polygons are valid from 0 Ma to 0 Ma. Active only at that instant, they
    # cover nearly the whole globe and would make the present-day land meaningless.
    shapes = [shape for shape in features(polygon_text, args.tolerance, args.min_points)
              if shape["from"] - shape["to"] > 1e-9]
    (directory / "continents.json").write_text(json.dumps(
        {"attribution": attribution, "layer": "continents",
         "tolerance_deg": args.tolerance, "features": shapes}, separators=(",", ":")))
    sequences = rotations([rotation_text])
    (directory / "rotations.json").write_text(json.dumps(
        {"attribution": attribution, "anchor": 0, "sequences": sequences},
        separators=(",", ":")))

    points = sum(len(ring) // 2 for shape in shapes for ring in shape["rings"])
    print(f"{MODEL}: {len(shapes)} polygons, {points} points, {len(sequences)} sequences")


if __name__ == "__main__":
    main()
