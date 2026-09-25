#!/usr/bin/env python3
"""Local preview: PhanDA HadCM3L model priors (Zenodo 8237751) on the elevation series.

Writes a derived directory that links every texture of `--base` and replaces two kinds:
`<id>-temp.png` gets the sea-surface temperature (`tos`) over the stop's sea, keeping the
Scotese air temperature over its land, and `<id>-climate-0.png` carries the annual
rainfall (`pr`) in the time windows' climate encoding (green = sqrt(mm / 8000) x 255,
red 0). Each stop takes the nearest model stage within 5 Myr; M1-M5 are averaged.
Not for release: the owner has not decided on the deposit's licence (issue #6).
"""
import argparse
import glob
import re
import sys
from pathlib import Path

import json
import netCDF4
import numpy as np
from PIL import Image
from scipy.interpolate import RegularGridInterpolator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_climate import RAIN_MAX_MM, fill_nearest  # noqa: E402
from scripts.build_paleodem import resample  # noqa: E402
from scripts.build_paleotemp import T_MAX, T_MIN  # noqa: E402

PHANDA = ROOT / "data/sources/phanda"
DEM = ROOT / "data/sources/paleodem/nc/Scotese_Wright_2018_Maps_1-88_1degX1deg_PaleoDEMS_nc_v2"
MAX_GAP_MA = 5.0
PRESENT = "paleodem-0000"      # its climate-0 texture is Krapp's 0 ka, kept


def stages(kind):
    found = {}
    for path in glob.glob(str(PHANDA / kind / f"scotese_02_*_M?_{kind}.nc")):
        found.setdefault(int(re.search(r"_(\d+)Ma_", path).group(1)), []).append(path)
    return found


def annual(paths, name):
    """Mean of the files' monthly climatologies, south first, longitudes 0..356.25."""
    values = np.mean([np.ma.filled(netCDF4.Dataset(p)[name][:].squeeze().mean(0).astype(float), np.nan)
                      for p in paths], axis=0)
    data = netCDF4.Dataset(paths[0])
    return np.asarray(data["latitude"][:], float), np.asarray(data["longitude"][:], float), values


def to_degree_grid(lat, lon, values):
    """Model cells, holes filled from the nearest kept cell, onto 181 x 361 north first,
    -180..180 inclusive: the shape `resample` expects."""
    values = fill_nearest(np.nan_to_num(values), ~np.isfinite(values))
    wide = np.concatenate([lon - 360, lon, lon + 360])
    grid = RegularGridInterpolator((lat, wide), np.concatenate([values] * 3, axis=1),
                                   bounds_error=False, fill_value=None)
    rows, cols = np.meshgrid(np.linspace(90, -90, 181), np.linspace(-180, 180, 361), indexing="ij")
    return grid(np.c_[rows.ravel(), cols.ravel()]).reshape(rows.shape)


def elevation(item):
    data = netCDF4.Dataset(DEM / item["file"])
    grid = next(v for v in data.variables.values() if v.ndim == 2)
    lat = next(v for k, v in data.variables.items() if k.lower().startswith("lat"))[:]
    z = np.asarray(grid[:], float)
    return z[::-1] if lat[0] < lat[-1] else z


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default=ROOT / "data/derived/paleodem", type=Path)
    parser.add_argument("--out", default=ROOT / "data/derived/paleodem-preview", type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    for path in args.base.iterdir():
        link = args.out / path.name
        if not link.exists() and not link.is_symlink():
            link.symlink_to(path.resolve())
    sst, rain = stages("tos"), stages("pr")
    for item in json.loads((ROOT / "sources/paleodem-slices.json").read_text())["maps"]:
        age = float(item["age_ma"])
        stage = min(sst, key=lambda s: abs(s - age))
        if abs(stage - age) > MAX_GAP_MA:
            print(f"{item['id']}  {age} Ma  no stage within {MAX_GAP_MA} Myr")
            continue
        sea = resample(elevation(item), 1024) <= 0
        temp_file = args.out / f"{item['id']}-temp.png"
        if temp_file.exists():
            air = np.asarray(Image.open(temp_file.resolve()), float) / 255 * (T_MAX - T_MIN) + T_MIN
            water = resample(to_degree_grid(*annual(sst[stage], "temp_mm_uo")), 1024)
            both = np.where(sea, water, air)
            temp_file.unlink()
            Image.fromarray(np.clip((both - T_MIN) / (T_MAX - T_MIN) * 255, 0, 255).astype(np.uint8)).save(temp_file)
        lat, lon, rate = annual(rain[stage], "precip_mm_srf")
        mm = resample(to_degree_grid(lat, lon, rate * 86400 * 365.25), 1024)
        rgb = np.zeros(mm.shape + (3,), np.uint8)
        rgb[..., 1] = np.round(np.sqrt(np.clip(mm, 0, RAIN_MAX_MM) / RAIN_MAX_MM) * 255)
        climate_file = args.out / f"{item['id']}-climate-0.png"
        if item["id"] == PRESENT:
            # Krapp has no rain on ice sheets (15000 mm = missing); its texture carries the
            # nearest land's value there. Put PhanDA's 0 Ma precipitation (snowfall included)
            # under the ice class instead and mark those cells in blue for the shader.
            krapp = np.array(Image.open((args.base / climate_file.name).resolve()).convert("RGB"))
            ice = np.round(krapp[..., 0] / 32.0) == 6
            snow = resample(to_degree_grid(lat, lon, rate * 86400 * 365.25), krapp.shape[1])
            krapp[..., 1][ice] = np.round(np.sqrt(np.clip(snow[ice], 0, RAIN_MAX_MM) / RAIN_MAX_MM) * 255)
            krapp[..., 2][ice] = 255
            rgb = krapp
            print(f"{item['id']}  present: {ice.mean():.1%} of the Krapp texture is ice, filled from PhanDA 0 Ma")
        if climate_file.is_symlink():
            climate_file.unlink()
        Image.fromarray(rgb).save(climate_file)
        print(f"{item['id']}  {age:5.0f} Ma  stage {stage} Ma  sea {sea.mean():.0%}  "
              f"sea mean {float(water[sea].mean()) if temp_file.exists() else float('nan'):5.1f} C  "
              f"land rain {float(mm[~sea].mean()):5.0f} mm")


if __name__ == "__main__":
    main()
