#!/usr/bin/env python3
"""Rasterise present-day ice onto the 0 Ma stop's texture grid.

Writes `paleodem-0000-ice.png`, 2048 x 1024 equirectangular RGB: red is grounded ice
(Natural Earth glaciated areas), green is floating shelf ice (Natural Earth Antarctic
ice shelves), both 255 inside a polygon and 0 outside. Longitude and latitude map
linearly to pixels, so no reprojection is needed. Polygon parts are filled one by one;
a part that is a hole is filled as ice too, which affects a few nunataks and nothing
else at this resolution. Only the present day has an open outline; see issue #7.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import shapefile
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "sources/ice.json"
WIDTH, HEIGHT = 2048, 1024


def rasterise(path, width=WIDTH, height=HEIGHT):
    image = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(image)
    reader = shapefile.Reader(str(path))
    for shape in reader.iterShapes():
        parts = list(shape.parts) + [len(shape.points)]
        for start, end in zip(parts, parts[1:]):
            ring = [((lon + 180.0) / 360.0 * width, (90.0 - lat) / 180.0 * height)
                    for lon, lat in shape.points[start:end]]
            if len(ring) >= 3:
                draw.polygon(ring, fill=255)
    return np.asarray(image)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=ROOT / "data/derived/paleodem", type=Path)
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text())
    folders = {asset["unzip"]: (ROOT / asset["path"]).parent / asset["unzip"] for asset in manifest["assets"]}
    grounded = rasterise(next(folders["glaciated"].glob("*.shp")))
    shelves = rasterise(next(folders["shelves"].glob("*.shp")))
    args.out.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.dstack([grounded, shelves, np.zeros_like(grounded)])).save(args.out / "paleodem-0000-ice.png")
    lat = np.cos(np.radians(90 - (np.arange(HEIGHT) + 0.5) / HEIGHT * 180))[:, None] * np.ones((HEIGHT, WIDTH))
    share = lambda mask: float(((mask > 0) * lat).sum() / lat.sum()) * 100
    print(f"grounded ice {share(grounded):.2f}% of the globe, shelves {share(shelves):.2f}% -> paleodem-0000-ice.png")


if __name__ == "__main__":
    main()
