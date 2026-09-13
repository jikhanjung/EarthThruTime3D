#!/usr/bin/env python3
"""Turn the Scotese 2021 temperature maps into per-slice textures and a global curve.

For every stop of the elevation timeline the nearest map by age, within 5 Myr, becomes
one 1024 x 512 grayscale PNG, `<id>-temp.png`, with surface air temperature encoded
over -60..60 C. The area-weighted global mean of every map is written to
`paleotemp-curve.json` as [age, mean C] pairs, oldest first, together with the mean
each stop was given. Maps are 1 degree; the texture is a bilinear resample of that.
"""
import argparse
import json
import re
import sys
from pathlib import Path

import netCDF4
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_paleodem import resample  # noqa: E402

MANIFEST = ROOT / "sources/paleotemp.json"
SLICES = ROOT / "sources/paleodem-slices.json"
T_MIN, T_MAX = -60.0, 60.0    # degrees C; the maps span -55..50
MAX_GAP_MA = 5.0


def temperature(path):
    """The map as rows north to south, columns -180 to 180, in degrees C."""
    data = netCDF4.Dataset(path)
    grid = next(v for k, v in data.variables.items() if v.ndim == 2)
    north = np.asarray(data.variables["northing"][:])
    values = np.asarray(grid[:], dtype=np.float32)
    return values[::-1] if north[0] < 0 else values


def global_mean(values):
    """Area-weighted mean over the 1 degree grid, weights by cos(latitude)."""
    latitude = np.linspace(90, -90, values.shape[0])
    weight = np.cos(np.radians(latitude))[:, None] * np.ones_like(values)
    return float((values * weight).sum() / weight.sum())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=ROOT / "data/derived/paleodem", type=Path)
    args = parser.parse_args()
    directory = ROOT / json.loads(MANIFEST.read_text())["directory"]
    maps = {}
    for path in sorted(directory.rglob("*_tas_*.nc")):
        maps[float(re.match(r"(\d+)_", path.name).group(1))] = path
    if not maps:
        raise SystemExit(f"No temperature maps in {directory}; run scripts/fetch_paleodem.py --manifest sources/paleotemp.json")
    args.out.mkdir(parents=True, exist_ok=True)
    means = {age: global_mean(temperature(path)) for age, path in maps.items()}
    stops = {}
    for item in json.loads(SLICES.read_text())["maps"]:
        age = float(item["age_ma"])
        nearest = min(maps, key=lambda candidate: abs(candidate - age))
        if abs(nearest - age) > MAX_GAP_MA:
            print(f"{item['id']}  {age} Ma  no map within {MAX_GAP_MA} Myr")
            continue
        fine = resample(temperature(maps[nearest]), 1024)
        encoded = np.clip((fine - T_MIN) / (T_MAX - T_MIN) * 255, 0, 255).astype(np.uint8)
        Image.fromarray(encoded).save(args.out / f"{item['id']}-temp.png")
        stops[item["id"]] = {"map_ma": nearest, "mean_c": round(means[nearest], 2)}
        print(f"{item['id']}  {age} Ma  map {nearest:.0f} Ma  mean {means[nearest]:5.1f} C")
    curve = {"source": "Scotese 2021, Zenodo 8238875, CC BY 4.0; area-weighted mean of each 1 degree map",
             "encoding": {"t_min_c": T_MIN, "t_max_c": T_MAX},
             "curve": [[age, round(mean, 2)] for age, mean in sorted(means.items(), reverse=True)],
             "stops": stops}
    (args.out / "paleotemp-curve.json").write_text(json.dumps(curve, indent=1) + "\n")
    print(f"{len(stops)} stops, {len(means)} maps, curve written")


if __name__ == "__main__":
    main()
