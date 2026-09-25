#!/usr/bin/env python3
"""Preview: symbols along today's named mountain ranges.

Natural Earth 10 m geography regions (public domain) carries 222 `Range/mtn` polygons with
names in many languages, Korean among them. For every range up to `--rank` (Natural
Earth's scale rank, 1 the largest), candidate points on a fine grid inside the polygon are
binned into cells of `--spacing` degrees (longitude widened by 1/cos latitude, so cells are
square on the ground) and the highest candidate of each cell is kept, so the marks sit on
the crest rather than fill the polygon. Height from the 6-minute PaleoDEM at 0 Ma, which
the page sizes the marks by. Writes static/core/mountain-ranges.json.

The past maps have no named ranges, so for every PaleoDEM stage but the present the marks
come from that map's own heights: a 0.5-degree block is mountain where its highest point
is at least `--past-height` metres and stands `--past-relief` metres above the lowland
around it (the 20th percentile of the block means within `--window` degrees, sea counted
as 0 m). The highest such block of each `--past-spacing`-degree cell gives the mark, and a
mark with no other mark within 320 km is dropped. An absolute height cut alone does not
carry into the past: PaleoDEM's older maps are far lower (at 250 Ma only 0.1 % of land is
above 2000 m), and it would erase Pangaea's ranges. Tuned on the 0 Ma map, where the rule's
marks come within 300 km of 92 % of the named ranges' marks.
"""
import argparse
import glob
import json
import re
import warnings
from pathlib import Path

import netCDF4
import numpy as np
import shapefile
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
SHAPES = ROOT / "data/sources/ranges/ne_10m_geography_regions_polys"
DEM = sorted(glob.glob(str(ROOT / "data/sources/paleodem/nc6/*/*_0Ma.nc")))[0]


def inside(lon, lat, rings):
    """Even-odd rule over every ring of the shape, vectorised over the points."""
    hit = np.zeros(lon.shape, bool)
    for ring in rings:
        x, y = ring[:, 0], ring[:, 1]
        x2, y2 = np.roll(x, -1), np.roll(y, -1)
        for xa, ya, xb, yb in zip(x, y, x2, y2):
            crosses = (ya > lat) != (yb > lat)
            with np.errstate(divide="ignore", invalid="ignore"):
                at = xa + (lat - ya) * (xb - xa) / (yb - ya)
            hit ^= crosses & (lon < at)
    return hit


def distance_km(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(np.radians, (lon1, lat1, lon2, lat2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371 * np.arcsin(np.sqrt(a))


def crest_marks(lats, lons, z, height, relief, window, spacing):
    """Marks from a map's own heights (see the module note)."""
    k = 5  # 0.5-degree blocks of the 0.1-degree grid
    ny, nx = (len(lats) - 1) // k, (len(lons) - 1) // k
    blocks = z[:ny * k, :nx * k].reshape(ny, k, nx, k)
    top = blocks.max((1, 3))
    land = np.where(blocks > 0, blocks, np.nan)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # all-sea blocks
        mean = np.nanmean(land, (1, 3))
    size = int(round(window / 0.5))
    low = ndimage.percentile_filter(np.nan_to_num(mean), 20, size=(size, size), mode="wrap")
    cells = {}
    for y, x in zip(*np.nonzero((top >= height) & (top - low >= relief))):
        a, c = np.unravel_index(blocks[y, :, x, :].argmax(), (k, k))
        lat, lon = float(lats[y * k + a]), float(lons[x * k + c])
        key = (int(np.floor((lat + 90) / spacing)), int(np.floor((lon + 180) * np.cos(np.radians(lat)) / spacing)))
        if key not in cells or top[y, x] > cells[key][2]:
            cells[key] = (lon, lat, float(top[y, x]))
    marks = np.array(list(cells.values())) if cells else np.zeros((0, 3))
    near = [(distance_km(m[0], m[1], marks[:, 0], marks[:, 1]) < 320).sum() >= 2 for m in marks]
    return [[round(m[0], 1), round(m[1], 1), int(m[2])] for m, keep in zip(marks, near) if keep]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rank", type=int, default=2)
    parser.add_argument("--spacing", type=float, default=2.0)
    parser.add_argument("--past-height", type=float, default=1000)
    parser.add_argument("--past-relief", type=float, default=900)
    parser.add_argument("--window", type=float, default=6.0)
    parser.add_argument("--past-spacing", type=float, default=3.0)
    parser.add_argument("--out", type=Path, default=ROOT / "static/core/mountain-ranges.json")
    args = parser.parse_args()
    dem = netCDF4.Dataset(DEM)
    lats, lons = np.asarray(dem["latitude"][:]), np.asarray(dem["longitude"][:])
    z = np.asarray(dem["z"][:], float)
    height = lambda lon, lat: z[np.abs(lats[:, None] - lat).argmin(0), np.abs(lons[:, None] - lon).argmin(0)]
    reader = shapefile.Reader(str(SHAPES))
    ranges = {}
    for shape, record in zip(reader.shapes(), reader.records()):
        if record["FEATURECLA"] != "Range/mtn" or record["SCALERANK"] > args.rank:
            continue
        points = np.asarray(shape.points)
        rings = [points[a:b] for a, b in zip(shape.parts, list(shape.parts[1:]) + [len(points)])]
        west, south, east, north = shape.bbox
        step = 0.2
        glon, glat = np.meshgrid(np.arange(west, east + step, step), np.arange(south, north + step, step))
        keep = inside(glon.ravel(), glat.ravel(), rings)
        lon, lat = glon.ravel()[keep], glat.ravel()[keep]
        if lon.size == 0:
            continue
        h = height(lon, lat)
        row = np.floor(lat / args.spacing)
        col = np.floor(lon * np.cos(np.radians((row + 0.5) * args.spacing)) / args.spacing)
        cells = {}
        for i, key in enumerate(zip(row, col)):
            if key not in cells or h[i] > h[cells[key]]:
                cells[key] = i
        marks = [[round(float(lon[i]), 2), round(float(lat[i]), 2), int(h[i])] for i in cells.values() if h[i] > 300]
        name = record["NAME_EN"] or record["NAME"]
        entry = ranges.setdefault(name, {"name": name, "name_ko": record["NAME_KO"], "rank": record["SCALERANK"], "marks": []})
        entry["marks"].extend(marks)
    past = {}
    for path in glob.glob(str(ROOT / "data/sources/paleodem/nc6/*/*Ma.nc")):
        age = float(re.search(r"_([\d.]+)Ma\.nc$", path).group(1))
        if age == 0:
            continue
        stage = netCDF4.Dataset(path)
        past[f"{age:g}"] = crest_marks(np.asarray(stage["latitude"][:]), np.asarray(stage["longitude"][:]),
                                        np.asarray(stage["z"][:], float), args.past_height, args.past_relief,
                                        args.window, args.past_spacing)
    out = {"source": "Natural Earth 10 m geography regions (public domain), Range/mtn; heights from PaleoDEM 0 Ma",
           "rank": args.rank, "spacing_deg": args.spacing, "ranges": sorted(ranges.values(), key=lambda r: (r["rank"], r["name"])),
           "past_source": "PaleoDEM (Scotese & Wright 2018) heights of each stage; see scripts/preview_ranges.py",
           "past_rule": {"height_m": args.past_height, "relief_m": args.past_relief, "window_deg": args.window,
                         "spacing_deg": args.past_spacing},
           "past": dict(sorted(past.items(), key=lambda item: float(item[0])))}
    args.out.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    total = sum(len(r["marks"]) for r in out["ranges"])
    print(f"{len(out['ranges'])} ranges, {total} marks -> {args.out}")
    print("past marks:", " ".join(f"{age}:{len(marks)}" for age, marks in out["past"].items() if float(age) % 50 == 0))
    for r in out["ranges"][:12]:
        hs = [m[2] for m in r["marks"]]
        print(f"  {r['name']:26s} {r['name_ko']:12s} marks {len(hs):3d}  max {max(hs) if hs else 0} m")


if __name__ == "__main__":
    main()
