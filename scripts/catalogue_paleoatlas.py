#!/usr/bin/env python3
"""Catalogue the map rasters inside the PALEOMAP PaleoAtlas for GPlates (Scotese 2016).

The same Zenodo archive already pinned by sources/plate-models/paleomap2016.json carries
90 paleogeographic maps as equirectangular JPEGs. This lists them, with the age and label
their file names give, into sources/paleomap-atlas-2016.json. Nothing is extracted to
disk: the segmentation reads members straight from the verified archive.

The archive is the only source of truth here. Ages are what the file names state, not a
re-reading of any timescale, and label quirks are recorded rather than corrected.
"""
import hashlib
import io
import json
import re
import sys
import zipfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_plate_model import manifest  # noqa: E402

OUT = ROOT / "sources/paleomap-atlas-2016.json"
RASTER = re.compile(r"PALEOMAP PaleoAtlas Rasters v3/Map(\d+)a\s+(.+?)_(\d+)\.jpg$")

# The Last Glacial Maximum file is numbered _001 like a 1 Ma map; it is the LGM,
# about 21 thousand years ago, which is how the 2002 maps catalogue it too.
LGM_AGE_MA = 0.021

# Quirks read off the file names on 2026-09-13, kept as notes rather than fixes.
NOTES = {
    27: "File name says 'EK Early Albian' at 120 Ma, between Late Aptian (115 Ma) and "
        "Barremian (125 Ma); the stage name looks like a slip for Aptian. Kept as given.",
    79: "Sits at 460 Ma next to map 80 at 461 Ma; both are Ordovician and one million "
        "years apart, as the file names give them.",
    80: "Sits at 461 Ma next to map 79 at 460 Ma, as the file names give them.",
}


def main():
    plate = manifest("paleomap2016")
    archive = plate["archive"]
    path = ROOT / archive["path"]
    data = path.read_bytes()
    if len(data) != archive["bytes"] or hashlib.sha256(data).hexdigest() != archive["sha256"]:
        raise SystemExit(f"{archive['path']} differs from the pinned plate manifest; "
                         "run scripts/fetch_plate_model.py paleomap2016 first.")

    maps = []
    with zipfile.ZipFile(io.BytesIO(data)) as bundle:
        for name in bundle.namelist():
            match = RASTER.search(name)
            if not match:
                continue
            number, label, suffix = int(match.group(1)), match.group(2).strip(), match.group(3)
            raw = bundle.read(name)
            with Image.open(io.BytesIO(raw)) as image:
                width, height = image.size
            lgm = "Glacial" in label
            age = LGM_AGE_MA if lgm else float(suffix)
            maps.append({
                "id": "paleoatlas-lgm" if lgm else f"paleoatlas-{int(suffix):03d}",
                "map_number": number,
                "label": label,
                "age_ma": age,
                "age_basis": ("Last Glacial Maximum; file suffix _001 read as about 21 ka"
                              if lgm else "file name suffix in millions of years"),
                "member": name,
                "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "width": width,
                "height": height,
                "notes": [NOTES[number]] if number in NOTES else [],
            })
    maps.sort(key=lambda item: item["age_ma"], reverse=True)
    if len({item["id"] for item in maps}) != len(maps):
        raise SystemExit("Two rasters map to the same id.")

    document = {
        "schema_version": 1,
        "dataset": "PALEOMAP PaleoAtlas for GPlates, map rasters (v3)",
        "author": "Christopher R. Scotese / PALEOMAP Project",
        "citation": plate["citation"],
        "archive": {"plate_manifest": "sources/plate-models/paleomap2016.json",
                    "path": archive["path"], "url": archive["url"],
                    "bytes": archive["bytes"], "sha256": archive["sha256"]},
        "license": {
            "name": plate["license"]["name"],
            "url": plate["license"]["url"],
            "source": plate["license"]["source"],
            "note": ("The Zenodo record lists CC BY 4.0. The record says the atlas was "
                     "originally published at earthbyte.org, and the PALEOMAP website's own "
                     "terms are narrower, so who attached the licence has not been "
                     "confirmed. Until it is, the original rasters are not served; only "
                     "this project's land fields derived from them are."),
        },
        "projection": {"name": "equirectangular",
                       "status": ("2:1 rasters covering 180W-180E, 90N-90S; land segmented "
                                  "from them aligns with the PALEOMAP plate polygons at "
                                  "0 to 3 degrees of spin-axis shift for 86 of 90 maps")},
        "processing": "Members are read from the verified archive; nothing is extracted to disk.",
        "maps": maps,
    }
    OUT.write_text(json.dumps(document, indent=1, ensure_ascii=False) + "\n")
    print(f"{OUT.relative_to(ROOT)}: {len(maps)} maps, "
          f"{maps[-1]['age_ma']:g}-{maps[0]['age_ma']:g} Ma")


if __name__ == "__main__":
    main()
