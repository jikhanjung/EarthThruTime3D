#!/usr/bin/env python3
"""Turn the 1° PaleoDEM grids into the viewer's field textures.

Each slice becomes one 1024 x 512 equirectangular RGB PNG: red is the same signed
coastline distance the segmentation writes, so mask mode and the stop table work
unchanged; green is elevation, quantised over -9000..6000 m so sea level sits at 0.6.
The DEM is bilinearly resampled from 1° to the texture grid before the sea-level cut,
so the coastline is the 0 m contour of the grid rather than a staircase of cells.
"""
import argparse
import json
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
    lon, lat, z = (np.asarray(data.variables[k][:]) for k in ("lon", "lat", "z"))
    if not (abs(lon[0] + 180) < 1e-6 and abs(abs(lat[0]) - 90) < 1e-6):
        raise SystemExit(f"Unexpected grid origin in {path.name}: lon {lon[0]}, lat {lat[0]}")
    return z[::-1] if lat[0] < 0 else z


def resample(z, width=FIELD_WIDTH):
    height = width // 2
    rows, cols = np.mgrid[0:height, 0:width]
    latitude = 90.0 - (rows + 0.5) / height * 180.0
    longitude = -180.0 + (cols + 0.5) / width * 360.0
    step_lat = 180.0 / (z.shape[0] - 1)
    step_lon = 360.0 / (z.shape[1] - 1)
    coords = [(90.0 - latitude) / step_lat, (longitude + 180.0) / step_lon]
    return ndimage.map_coordinates(z, coords, order=1, mode="nearest")


def texture(z):
    fine = resample(z)
    field = signed_distance(fine > 0)
    height = np.clip((fine - Z_MIN) / (Z_MAX - Z_MIN) * 255, 0, 255).astype(np.uint8)
    return np.dstack([field, height, np.zeros_like(field)])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=ROOT / "data/derived/segmentation", type=Path)
    parser.add_argument("ids", nargs="*", help="slice ids to build; default all")
    args = parser.parse_args()
    catalogue = json.loads(CATALOGUE.read_text())
    args.out.mkdir(parents=True, exist_ok=True)
    for item in catalogue["slices"]:
        if args.ids and item["id"] not in args.ids:
            continue
        z = elevation(ROOT / catalogue["directory"] / item["file"])
        Image.fromarray(texture(z)).save(args.out / f"{item['id']}-field.png")
        print(f"{item['id']}  {item['age_ma']} Ma  land {(z > 0).mean():.1%}")


if __name__ == "__main__":
    main()
