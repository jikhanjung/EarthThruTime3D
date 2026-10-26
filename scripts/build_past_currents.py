"""Past surface currents for the PaleoDEM stops, from Pohl's FOAM runs (wwolf P02 step 3).

FOAM was run every 20 Myr from 540 to 0 Ma on the Scotese & Wright (2018) geographies with
CO2, the Sun, the orbit and the land surface held fixed (sources/foam-currents.json), so its
currents show what the continents do, not each period's climate. Each PaleoDEM stop older than
the present takes the annual mean of the top level (-10 m) of the nearest run, the younger one
on a tie. The present keeps the ECCO2 mean (jikhanjung P10).

The field is the one P10's particles read: an RGB PNG of 1-degree cells, north first from
-180, R = u and G = v over symmetric ranges (code 128 is exactly zero), B = 255 where the
stop's own map is sea. Sea is the map's, not the model's: FOAM's 2.8-degree coast differs from
the grid's, so its flow is carried into the map's sea from the nearest model sea cell, and a
particle lives and dies by the coast the page draws.

Writes data/derived/paleodem/<id>-currents.png and currents.json (each stop's run and ranges).
"""
import argparse
import json
import sys
from pathlib import Path

import netCDF4
import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.interpolate import RegularGridInterpolator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_paleodem import CATALOGUE, default_source, elevation, locate  # noqa: E402

MANIFEST = ROOT / "sources/foam-currents.json"
OUT = ROOT / "data/derived/paleodem"
LON = np.arange(-179.5, 180, 1.0)
LAT = np.arange(89.5, -90, -1.0)


def foam_surface(path):
    """Annual mean of the top level as (u, v, sea) on FOAM's grid, latitude south first,
    longitude 0 to 360."""
    data = netCDF4.Dataset(path)
    top = int(np.argmax(np.asarray(data["lev"][:])))           # -10 m, the shallowest
    u, v = (np.ma.filled(data[name][:, top].mean(0), np.nan) for name in ("U", "V"))
    return np.asarray(data["lon"][:], float), np.asarray(data["lat"][:], float), u, v


def fill_land(a):
    """Every land cell takes its nearest sea cell's value, across the date line too."""
    wide = np.concatenate([a, a, a], axis=1)
    _, (rows, cols) = ndimage.distance_transform_edt(~np.isfinite(wide), return_indices=True)
    width = a.shape[1]
    return wide[rows, cols][:, width:2 * width]


def to_cells(lon, lat, a):
    """Bilinear onto the 1-degree cell centres, wrapping in longitude."""
    x = np.concatenate([[lon[-1] - 360], lon, [lon[0] + 360]])
    padded = np.concatenate([a[:, -1:], a, a[:, :1]], axis=1)
    interpolate = RegularGridInterpolator((lat, x), padded)
    la = np.clip(LAT, lat.min(), lat.max())
    points = np.stack(np.meshgrid(la, np.mod(LON, 360), indexing="ij"), -1)
    return interpolate(points)


def map_sea(z):
    """1-degree cells (north first, from -180) where most of the grid lies below 0 m. The
    grids are node-registered, rows north to south and columns -180 to 180."""
    below = (z < 0).astype(float)
    step = (z.shape[1] - 1) // 360
    if step >= 2:
        cells = below[:-1, :-1].reshape(180, step, 360, step).mean(axis=(1, 3))
    else:                                         # the 1-degree set: average the four corners
        cells = (below[:-1, :-1] + below[1:, :-1] + below[:-1, 1:] + below[1:, 1:]) / 4
    return cells >= 0.5


def symmetric(largest):
    """A range whose code 128 is exactly zero, as P10's ECCO2 mean: -M·128/127 .. M."""
    m = max(largest, 1e-3)
    return [-m * 128 / 127, m]


def encode(u, v, sea):
    rgb = np.zeros((180, 360, 3), np.uint8)
    ranges = {}
    for i, (key, grid) in enumerate((("u", u), ("v", v))):
        lo, hi = symmetric(float(np.abs(grid[sea]).max()) if sea.any() else 0)
        rgb[..., i] = np.rint((np.clip(grid, lo, hi) - lo) / (hi - lo) * 255)
        ranges[key] = [round(lo, 6), round(hi, 6)]
    rgb[..., 2] = np.where(sea, 255, 0)
    return rgb, ranges


def nearest_run(age, runs):
    return min(runs, key=lambda run: (abs(run - age), run))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", default=OUT, type=Path)
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text())
    runs = {int(asset["role"].split("-")[1][:-2]): ROOT / asset["path"] for asset in manifest["assets"]}
    missing = [path for path in runs.values() if not path.exists()]
    if missing:
        raise SystemExit(f"Missing {len(missing)} FOAM files; run scripts/fetch_paleodem.py --manifest "
                         f"{MANIFEST.relative_to(ROOT)}")
    catalogue = json.loads(CATALOGUE.read_text())
    directory = default_source(catalogue)
    surfaces = {}
    maps = {}
    for item in catalogue["maps"]:
        if item["age_ma"] == 0:
            continue
        run = nearest_run(item["age_ma"], runs)
        if run not in surfaces:
            lon, lat, u, v = foam_surface(runs[run])
            surfaces[run] = (to_cells(lon, lat, fill_land(u)), to_cells(lon, lat, fill_land(v)),
                             to_cells(lon, lat, np.where(np.isfinite(u), 1.0, 0.0)) >= 0.5)
        u, v, model_sea = surfaces[run]
        sea = map_sea(elevation(locate(directory, item)))
        rgb, ranges = encode(u, v, sea)
        Image.fromarray(rgb, "RGB").save(args.out / f"{item['id']}-currents.png", optimize=True)
        # The share of the map's sea where the model has land, its flow carried in from the
        # nearest model sea; a measure of how far the run's coast is from the map's.
        carried = float((sea & ~model_sea).sum() / max(sea.sum(), 1))
        maps[item["id"]] = {"run_ma": run, **ranges, "carried": round(carried, 3)}
    out = {"source": manifest["cite"], "license": manifest["license"], "record": manifest["record"],
           "depth_m": 10, "maps": maps}
    (args.out / "currents.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    carried = [m["carried"] for m in maps.values()]
    print(f"{len(maps)} stops from {len(surfaces)} FOAM runs -> {args.out.relative_to(ROOT) if args.out.is_relative_to(ROOT) else args.out}")
    print(f"map sea carried in from the nearest model sea: median {np.median(carried):.1%}, max {max(carried):.1%}")


if __name__ == "__main__":
    main()
