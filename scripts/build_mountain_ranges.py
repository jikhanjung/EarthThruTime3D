#!/usr/bin/env python3
"""Mountain-range marks for the flat maps' raised-relief switch.

Usage: .venv/bin/python scripts/build_mountain_ranges.py
(after scripts/fetch_paleodem.py --manifest sources/mountain-ranges.json and the PaleoDEM
grids of sources/paleodem.json). Writes data/derived/paleodem/mountain-ranges.json.

The present: Natural Earth's named ranges (Range/mtn) up to scale rank 2. Candidate points
on a 0.2-degree grid inside each polygon are binned into 2-degree cells (longitude widened
by 1/cos latitude, so a cell is square on the ground) and the highest of each cell is kept,
so the marks follow the crest rather than fill the polygon. Height from the present grid.

The past grids have no named ranges, so their marks come from each grid's own heights: a
0.5-degree block is mountain where its highest point is at least 1000 m and stands 900 m
above the lowland around it (the 20th percentile of the block means within 6 degrees, the
sea counted as 0 m). The highest such block of each 3-degree cell gives the mark, and a
mark with no other within 320 km is dropped. A height cut alone does not carry into the
past: the older grids are far lower (at 250 Ma only 0.1 % of land is above 2000 m). On the
present grid the rule's marks come within 300 km of 92 % of the named ranges' marks
(devlog wwolf 018); the named set is kept at the present because it is curated.
"""
import argparse
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import shapefile
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_paleodem import CATALOGUE, default_source, elevation, locate  # noqa: E402

MANIFEST = ROOT / "sources/mountain-ranges.json"
RANK = 2              # Natural Earth scale rank kept at the present
NAMED_SPACING = 2.0   # degrees between the present's marks
HEIGHT = 1000.0       # past rule: block top, metres
RELIEF = 900.0        # past rule: top above the surrounding lowland, metres
WINDOW = 6.0          # past rule: the surround, degrees
SPACING = 3.0         # past rule: degrees between marks
NEIGHBOUR_KM = 320.0  # past rule: a mark with no other this near is dropped


def distance_km(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(np.radians, (lon1, lat1, lon2, lat2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371 * np.arcsin(np.sqrt(a))


def axes(z):
    """Latitudes (north to south) and longitudes of a grid as elevation() returns it."""
    return np.linspace(90, -90, z.shape[0]), np.linspace(-180, 180, z.shape[1])


def inside(lon, lat, rings):
    """Even-odd rule over every ring of a shape, vectorised over the points."""
    hit = np.zeros(lon.shape, bool)
    for ring in rings:
        x, y = ring[:, 0], ring[:, 1]
        for xa, ya, xb, yb in zip(x, y, np.roll(x, -1), np.roll(y, -1)):
            crosses = (ya > lat) != (yb > lat)
            with np.errstate(divide="ignore", invalid="ignore"):
                at = xa + (lat - ya) * (xb - xa) / (yb - ya)
            hit ^= crosses & (lon < at)
    return hit


def named_marks(shapes, z):
    """The present: marks along the crest of each named range, grouped by range."""
    lats, lons = axes(z)
    height = lambda lon, lat: z[np.abs(lats[:, None] - lat).argmin(0), np.abs(lons[:, None] - lon).argmin(0)]
    reader = shapefile.Reader(str(shapes))
    ranges = {}
    for shape, record in zip(reader.shapes(), reader.records()):
        if record["FEATURECLA"] != "Range/mtn" or record["SCALERANK"] > RANK:
            continue
        points = np.asarray(shape.points)
        rings = [points[a:b] for a, b in zip(shape.parts, list(shape.parts[1:]) + [len(points)])]
        west, south, east, north = shape.bbox
        glon, glat = np.meshgrid(np.arange(west, east + 0.2, 0.2), np.arange(south, north + 0.2, 0.2))
        keep = inside(glon.ravel(), glat.ravel(), rings)
        lon, lat = glon.ravel()[keep], glat.ravel()[keep]
        if lon.size == 0:
            continue
        h = height(lon, lat)
        row = np.floor(lat / NAMED_SPACING)
        col = np.floor(lon * np.cos(np.radians((row + 0.5) * NAMED_SPACING)) / NAMED_SPACING)
        cells = {}
        for i, key in enumerate(zip(row, col)):
            if key not in cells or h[i] > h[cells[key]]:
                cells[key] = i
        marks = [[round(float(lon[i]), 2), round(float(lat[i]), 2), int(h[i])] for i in cells.values() if h[i] > 300]
        name = record["NAME_EN"] or record["NAME"]
        entry = ranges.setdefault(name, {"name": name, "name_ko": record["NAME_KO"], "marks": []})
        entry["marks"].extend(marks)
    return sorted(ranges.values(), key=lambda r: r["name"])


def crest_marks(z):
    """A past grid: marks where the ground is high and stands above its surroundings."""
    lats, lons = axes(z)
    k = max(1, round(0.5 / (180 / (z.shape[0] - 1))))   # cells per 0.5-degree block
    ny, nx = (len(lats) - 1) // k, (len(lons) - 1) // k
    blocks = z[:ny * k, :nx * k].reshape(ny, k, nx, k)
    top = blocks.max((1, 3))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # all-sea blocks
        mean = np.nanmean(np.where(blocks > 0, blocks, np.nan), (1, 3))
    size = max(1, round(WINDOW / (k * 180 / (z.shape[0] - 1))))
    low = ndimage.percentile_filter(np.nan_to_num(mean), 20, size=(size, size), mode="wrap")
    cells = {}
    for y, x in zip(*np.nonzero((top >= HEIGHT) & (top - low >= RELIEF))):
        a, c = np.unravel_index(blocks[y, :, x, :].argmax(), (k, k))
        lat, lon = float(lats[y * k + a]), float(lons[x * k + c])
        key = (int(np.floor((lat + 90) / SPACING)), int(np.floor((lon + 180) * np.cos(np.radians(lat)) / SPACING)))
        if key not in cells or top[y, x] > cells[key][2]:
            cells[key] = (lon, lat, float(top[y, x]))
    marks = np.array(list(cells.values())) if cells else np.zeros((0, 3))
    near = [(distance_km(m[0], m[1], marks[:, 0], marks[:, 1]) < NEIGHBOUR_KM).sum() >= 2 for m in marks]
    return [[round(m[0], 1), round(m[1], 1), int(m[2])] for m, keep in zip(marks, near) if keep]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default=ROOT / "data/derived/paleodem/mountain-ranges.json", type=Path)
    args = parser.parse_args()
    asset = json.loads(MANIFEST.read_text())["assets"][0]
    shapes = (ROOT / asset["path"]).parent / asset["unzip"] / asset["layer"]
    if not shapes.with_suffix(".shp").exists():
        raise SystemExit(f"Missing {shapes}.shp; run scripts/fetch_paleodem.py --manifest {MANIFEST.relative_to(ROOT)}")
    catalogue = json.loads(CATALOGUE.read_text())
    directory = default_source(catalogue)
    maps = {}
    present = None
    for item in catalogue["maps"]:
        z = elevation(locate(directory, item))
        if item["age_ma"] == 0:
            present = named_marks(shapes, z)
            check = crest_marks(z)
        else:
            maps[item["id"]] = crest_marks(z)
    named = np.array([m[:2] for r in present for m in r["marks"]])
    rule = np.array([m[:2] for m in check])
    reach = np.mean([distance_km(x, y, rule[:, 0], rule[:, 1]).min() < 300 for x, y in named])
    out = {"source": f"{asset['cite']} ({asset['license']}); PaleoDEM grids (Scotese & Wright 2018, CC BY 4.0)",
           "rule": {"height_m": HEIGHT, "relief_m": RELIEF, "window_deg": WINDOW, "spacing_deg": SPACING,
                    "neighbour_km": NEIGHBOUR_KM, "named_rank": RANK, "named_spacing_deg": NAMED_SPACING,
                    "present_named_within_300km": round(float(reach), 3)},
           "present": present, "maps": maps}
    args.out.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    print(f"{len(present)} named ranges, {len(named)} marks at the present; the rule reaches {reach:.0%} of them")
    print("past marks:", " ".join(f"{i.split('-')[1]}:{len(m)}" for i, m in maps.items() if int(i.split('-')[1]) % 500 == 0))
    print(f"-> {args.out.relative_to(ROOT) if args.out.is_relative_to(ROOT) else args.out} ({args.out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
