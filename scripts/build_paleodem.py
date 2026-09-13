#!/usr/bin/env python3
"""Turn the 1° PaleoDEM grids into the viewer's field textures.

Each slice becomes one equirectangular RGB PNG, 1024 x 512 by default: red is the same
signed coastline distance the segmentation writes, so mask mode and the stop table work
unchanged; green is elevation, quantised over -9000..6000 m so sea level sits at 0.6.
The DEM is bilinearly resampled to the texture grid before the sea-level cut, so the
coastline is the 0 m contour of the grid rather than a staircase of cells.

The 1° grids carry nothing beyond 1024 wide. For a sharper texture point --source at
the 6-minute grids and ask for --width 2048; slices are matched by age, so the file
names need not be the ones the catalogue lists.
"""
import argparse
import json
import re
import sys
from pathlib import Path

import netCDF4
import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.segment_landmass import FIELD_WIDTH, signed_distance  # noqa: E402

CATALOGUE = ROOT / "sources/paleodem-slices.json"
Z_MIN, Z_MAX = -9000.0, 6000.0   # metres; the grids' own range, sea level at 0.6


def elevation(path):
    """The grid as rows north to south, columns -180 to 180, in metres."""
    data = netCDF4.Dataset(path)
    # The 1° files name the axes lon/lat, the 6-minute files longitude/latitude.
    axes = {name[:3]: name for name in data.variables if name[:3] in ("lon", "lat")}
    lon, lat, z = (np.asarray(data.variables[k][:]) for k in (axes["lon"], axes["lat"], "z"))
    if not (abs(lon[0] + 180) < 1e-6 and abs(abs(lat[0]) - 90) < 1e-6):
        raise SystemExit(f"Unexpected grid origin in {path.name}: lon {lon[0]}, lat {lat[0]}")
    return z[::-1] if lat[0] < 0 else z


def locate(directory, item):
    """The slice's grid in `directory`, by catalogue name or, failing that, by age."""
    exact = directory / item["file"]
    if exact.exists():
        return exact
    # The 6-minute set rounds 385.2 and 390.5 Ma to whole numbers, so match within a
    # million years; slices are five apart, so nothing else can be that close.
    wanted = float(item["age_ma"])
    for path in sorted(directory.glob("*.nc")):
        found = re.search(r"(\d+(?:\.\d+)?)\s*Ma\.nc$", path.name)
        if found and abs(float(found.group(1)) - wanted) < 1.0:
            return path
    raise SystemExit(f"No grid for {item['id']} ({wanted} Ma) in {directory}")


def resample(z, width=FIELD_WIDTH):
    height = width // 2
    rows, cols = np.mgrid[0:height, 0:width]
    latitude = 90.0 - (rows + 0.5) / height * 180.0
    longitude = -180.0 + (cols + 0.5) / width * 360.0
    step_lat = 180.0 / (z.shape[0] - 1)
    step_lon = 360.0 / (z.shape[1] - 1)
    coords = [(90.0 - latitude) / step_lat, (longitude + 180.0) / step_lon]
    return ndimage.map_coordinates(z, coords, order=1, mode="nearest")


def texture(z, width=FIELD_WIDTH):
    fine = resample(z, width)
    field = signed_distance(fine > 0)
    height = np.clip((fine - Z_MIN) / (Z_MAX - Z_MIN) * 255, 0, 255).astype(np.uint8)
    return np.dstack([field, height, np.zeros_like(field)])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=ROOT / "data/derived/segmentation", type=Path)
    parser.add_argument("--source", type=Path, help="directory of grids; default the catalogue's 1° set")
    parser.add_argument("--width", type=int, default=FIELD_WIDTH, choices=(1024, 2048, 4096))
    parser.add_argument("ids", nargs="*", help="slice ids to build; default all")
    args = parser.parse_args()
    catalogue = json.loads(CATALOGUE.read_text())
    directory = args.source or ROOT / catalogue["directory"]
    args.out.mkdir(parents=True, exist_ok=True)
    for item in catalogue["slices"]:
        if args.ids and item["id"] not in args.ids:
            continue
        z = elevation(locate(directory, item))
        Image.fromarray(texture(z, args.width)).save(args.out / f"{item['id']}-field.png")
        print(f"{item['id']}  {item['age_ma']} Ma  land {(z > 0).mean():.1%}")


if __name__ == "__main__":
    main()
