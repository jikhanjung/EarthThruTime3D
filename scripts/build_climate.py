#!/usr/bin/env python3
"""Turn Krapp et al. 2021 into one climate texture per thousand years of the time windows.

For every age from 0 to 130 ka the present grid gets `paleodem-0000-climate-<age>.png`:
720 x 360, the source's own 0.5 degree cells, north first, never smoothed. Red is the plant
cover class the BIOME4 biome folds into, times 32; green is annual precipitation as
sqrt(mm / 8000) x 255, so the dry end keeps its detail. The source steps once per thousand
years, which is the windows' own step, so no age is interpolated.

The classes, an order of plant cover plus the two cold ones (BIOME4 codes in brackets):
0 desert and barren (21, 27), 1 dry shrubland (13, 14), 2 grassland (19, 20), 3 savanna,
woodland and parkland (12, 15, 16, 17, 18), 4 forest (1-11), 5 tundra (22-26), 6 land ice (28).

The source is land only, on its own coast for each age; the page cuts the coast from today's
heights and the age's sea level, which is finer and not the same line. So every sea cell
takes the nearest land cell's values, and whatever the page calls land has a climate under
it. Precipitation is missing (15000 mm, the source's known issue) under ice and over large
lakes; it is filled the same way, and the page draws the ice class there instead of rain.

A model, not a reconstruction: a statistical emulator of HadCM3 snapshots. Its Sahara stays
desert through the African Humid Period (devlog wwolf 013); the page says so.
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
MANIFEST = ROOT / "sources/quaternary-climate.json"
PRESENT = "paleodem-0000"
OLDEST_KA = 130
RAIN_MAX_MM = 8000.0          # the source's highest real value is 8017
RAIN_MISSING_MM = 15000.0     # known_issues.md: ice sheets and masked lakes
CLASS_STEP = 32
CLASSES = {0: (21, 27), 1: (13, 14), 2: (19, 20), 3: (12, 15, 16, 17, 18),
           4: tuple(range(1, 12)), 5: (22, 23, 24, 25, 26), 6: (28,)}
WRAP = 90                     # columns repeated either side so the fill crosses the date line


def cover_class(biome):
    """BIOME4 codes to plant cover classes; -1 where the source has no land."""
    out = np.full(biome.shape, -1, np.int16)
    for cover, codes in CLASSES.items():
        out[np.isin(biome, codes)] = cover
    return out


def fill_nearest(values, missing):
    """`values` with every `missing` cell given the nearest kept cell's value.
    Nearest in cell space, not on the sphere; it only feeds a coastal fringe."""
    if not missing.any():
        return values
    if missing.all():
        raise ValueError("Nothing to fill from")
    wide = np.pad(missing, ((0, 0), (WRAP, WRAP)), mode="wrap")
    index = ndimage.distance_transform_edt(wide, return_distances=False, return_indices=True)
    return np.pad(values, ((0, 0), (WRAP, WRAP)), mode="wrap")[tuple(index)][:, WRAP:-WRAP]


def encode(biome, rain_mm):
    """One RGB texture from a slice's biome codes and annual precipitation, both south first."""
    cover = cover_class(biome)
    cover = fill_nearest(cover, cover < 0)
    missing = ~np.isfinite(rain_mm) | (rain_mm >= RAIN_MISSING_MM)
    rain = fill_nearest(np.where(missing, 0.0, rain_mm), missing)
    green = np.round(np.sqrt(np.clip(rain, 0, RAIN_MAX_MM) / RAIN_MAX_MM) * 255)
    rgb = np.zeros(cover.shape + (3,), np.uint8)
    rgb[..., 0] = cover * CLASS_STEP
    rgb[..., 1] = green
    return rgb[::-1]            # north first, as every texture of the page is


def slice_at(dataset, name, age_ka):
    years = np.asarray(dataset["time"][:])
    index = int(np.argmin(np.abs(years + age_ka * 1000)))
    if abs(years[index] + age_ka * 1000) > 1:
        raise ValueError(f"No {age_ka} ka slice in the source")
    values = dataset[name][index]
    return np.ma.filled(values, np.nan if values.dtype.kind == "f" else 0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=ROOT / "data/derived/paleodem", type=Path)
    parser.add_argument("--oldest", default=OLDEST_KA, type=int, help="oldest age to build, ka")
    args = parser.parse_args()
    directory = ROOT / json.loads(MANIFEST.read_text())["directory"]
    paths = [directory / "biome4output_800ka.nc", directory / "bio12_800ka.nc"]
    if not all(path.exists() for path in paths):
        raise SystemExit(f"Source missing in {directory}; run scripts/fetch_paleodem.py --manifest {MANIFEST.relative_to(ROOT)}")
    biomes, rains = (netCDF4.Dataset(path) for path in paths)
    args.out.mkdir(parents=True, exist_ok=True)
    for age in range(args.oldest + 1):
        biome = slice_at(biomes, "biome", age)
        texture = encode(biome, slice_at(rains, "bio12", age).astype(np.float64))
        Image.fromarray(texture).save(args.out / f"{PRESENT}-climate-{age}.png", optimize=True)
        land = cover_class(biome) >= 0
        share = (cover_class(biome)[land] == 0).mean() * 100
        print(f"{age:4d} ka  land cells {land.sum():6d}  desert {share:4.1f}% of them")
    print(f"{args.oldest + 1} textures in {args.out}")


if __name__ == "__main__":
    sys.exit(main())
