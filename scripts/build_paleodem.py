#!/usr/bin/env python3
"""Turn the 1° PaleoDEM grids into the viewer's field textures.

Each slice becomes one equirectangular RGB PNG, 1024 x 512 by default: red is the same
signed coastline distance the segmentation writes, so mask mode and the stop table work
unchanged; green is the high byte of elevation over -9000..6000 m, so sea level sits
at 0.6, and blue holds four more bits (--bits 12, 3.7 m steps, files 1.8x larger) or
nothing (--bits 8, 59 m steps, files 1.8x smaller). The viewer decodes both the same
way, so an 8-bit texture reads 9 m low, below its own step. 8 is the default, chosen
by the owner to keep the runtime bundle small (about 83 MB against 150 MB); the cost is
that the sea-level control cuts the coast from 59 m height steps. For shading alone the
two renders differ by one grey level. Pass --bits 12 for the finer set. The present grid
is written at 12 bits whatever --bits says: the time windows of the last glacial cycle
move the sea over it by more than a hundred metres, which 59 m steps would reduce to two
jumps of the coast, and one finer texture costs about 1.5 MB.
The DEM is bilinearly resampled to the texture grid before the sea-level cut, so the
coastline is the 0 m contour of the grid rather than a staircase of cells.

The 1° grids carry nothing beyond 1024 wide: at 2048 every cell is a block six pixels
across, and the Caspian comes out as Lego. So the 6-minute grids are used whenever
they have been fetched (`scripts/fetch_paleodem.py` unpacks them beside the 1° set),
and the 1° set only when they have not; --source overrides either way. The pinned
6-minute archive holds all 109 slices, 385.2 and 390.5 Ma rounded to whole numbers,
which the lookup matches by age, so the file names need not be the ones the catalogue
lists.
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
from scripts.segment_paleoatlas import FIELD_WIDTH, signed_field  # noqa: E402

CATALOGUE = ROOT / "sources/paleodem-slices.json"
Z_MIN, Z_MAX = -9000.0, 6000.0   # metres; the grids' own range, sea level at 0.6
PRESENT_BITS = 12                # the grid the time windows move the sea over


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


def default_source(catalogue):
    """The 6-minute grids when they have been fetched, else the catalogue's 1° set."""
    for asset in json.loads((ROOT / "sources/paleodem.json").read_text())["assets"]:
        if "6min" in asset["path"] and "unzip" in asset:
            unpacked = (ROOT / asset["path"]).parent / asset["unzip"]
            for directory in sorted(unpacked.glob("*/")):
                if any(directory.glob("*.nc")):
                    return directory
    return ROOT / catalogue["directory"]


def resample(z, width=FIELD_WIDTH):
    height = width // 2
    rows, cols = np.mgrid[0:height, 0:width]
    latitude = 90.0 - (rows + 0.5) / height * 180.0
    longitude = -180.0 + (cols + 0.5) / width * 360.0
    step_lat = 180.0 / (z.shape[0] - 1)
    step_lon = 360.0 / (z.shape[1] - 1)
    coords = [(90.0 - latitude) / step_lat, (longitude + 180.0) / step_lon]
    return ndimage.map_coordinates(z, coords, order=1, mode="nearest")


def texture(z, width=FIELD_WIDTH, bits=12):
    fine = resample(z, width)
    field, _ = signed_field(fine > 0, width)
    height = np.clip((fine - Z_MIN) / (Z_MAX - Z_MIN) * 4095, 0, 4095).astype(np.uint16)
    low = ((height & 15) if bits == 12 else np.zeros_like(height)).astype(np.uint8)
    return np.dstack([field, (height >> 4).astype(np.uint8), low])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=ROOT / "data/derived/paleodem", type=Path)
    parser.add_argument("--source", type=Path,
                        help="directory of grids; default the 6-minute set when fetched, else the 1° set")
    parser.add_argument("--width", type=int, default=FIELD_WIDTH, choices=(1024, 2048, 4096))
    parser.add_argument("--bits", type=int, default=8, choices=(8, 12), help="height precision")
    parser.add_argument("ids", nargs="*", help="slice ids to build; default all")
    args = parser.parse_args()
    catalogue = json.loads(CATALOGUE.read_text())
    directory = args.source or default_source(catalogue)
    print(f"grids from {directory.relative_to(ROOT) if directory.is_relative_to(ROOT) else directory}")
    args.out.mkdir(parents=True, exist_ok=True)
    for item in catalogue["maps"]:
        if args.ids and item["id"] not in args.ids:
            continue
        z = elevation(locate(directory, item))
        bits = PRESENT_BITS if item["age_ma"] == 0 else args.bits
        Image.fromarray(texture(z, args.width, bits)).save(args.out / f"{item['id']}-field.png")
        print(f"{item['id']}  {item['age_ma']} Ma  land {(z > 0).mean():.1%}  {bits}-bit")


if __name__ == "__main__":
    main()
