"""The present-day circulation schematic and overturning sections (wwolf P02 step 5).

Two parts, one file for the page:

- The schematic: the textbook "conveyor belt" drawn from the literature, not traced from data
  (Broecker 1991, doi:10.5670/oceanog.1991.07; Rahmstorf 2002, doi:10.1038/nature01090). The
  warm upper limb runs from where deep water rises in the North Pacific through the Indonesian
  passages (joined by the Indian Ocean's shallow cell, Schott et al. 2002,
  doi:10.1016/S0079-6611(02)00039-3), round South Africa and up the Atlantic to the Nordic and
  Labrador Seas. North Atlantic Deep Water runs from where it sinks south along the Americas,
  east with the circumpolar current and north into the Indian and Pacific Oceans. Antarctic
  Bottom Water runs from the Weddell and Ross Seas, the Adelie coast and Cape Darnley (Orsi et
  al. 1999, doi:10.1016/S0079-6611(99)00004-X; Ohshima et al. 2013, doi:10.1038/ngeo1738) north
  along the sea floor under the deep water, and fades out: it mixes upward as it spreads, with
  no single end. Every other line starts and ends at a mark (where water sinks or rises) or on
  another line; where lines cross they are at different depths. Most deep water actually rises
  in the Southern Ocean, slowly and over a wide area (Marshall & Speer 2012,
  doi:10.1038/ngeo1391), which no line can show.
- The sections: the Atlantic and Indo-Pacific overturning streamfunction north of 32 S from
  the NCEP GODAS reanalysis, 2016-2020 mean (sources/godas.json), the data behind the picture.

Every point of the schematic must lie in the present grid's sea, or the build stops.
Writes data/derived/paleodem/circulation.json.
"""
import argparse
import json
import sys
from pathlib import Path

import netCDF4
import numpy as np
from scipy import ndimage
from scipy.ndimage import uniform_filter1d
from skimage import measure

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_paleodem import CATALOGUE, default_source, elevation, locate  # noqa: E402

MANIFEST = ROOT / "sources/godas.json"
OUT = ROOT / "data/derived/paleodem"

# (layer, waypoints (lon, lat), fades out). Smoothed into curves by smooth_path.
CONVEYOR = [
    ("surface", [(162, 40), (159, 33), (155, 25), (148, 17), (139, 10), (133, 6), (127, 3.5),
                 (121, 1.5), (119.7, 1), (118.8, -0.5), (118.3, -3.5), (118.2, -4.6), (118.7, -5.6),
                 (119.2, -6.4), (119.1, -7.5), (117.8, -8), (116.3, -8), (115.8, -8.35), (115.75, -8.5),
                 (115.7, -8.7), (115.7, -9.2), (115.1, -10), (111, -13), (95, -14), (75, -15),
                 (62, -14.3), (57, -14.6), (54, -15.5), (51.3, -14.3), (50.3, -11.4),
                 (47.5, -12.2), (45.4, -13.6), (43, -14), (41, -19), (36, -26), (31, -31),
                 (25, -36), (18, -37), (12, -31), (5, -22), (-5, -14), (-18, -9),
                 (-31, -5), (-40, 0), (-48, 4), (-56, 9), (-64, 13.5), (-75, 15),
                 (-83, 18.5), (-86, 22.5), (-86, 25.5), (-82.5, 24.2), (-81, 24.25), (-79.95, 24.9),
                 (-79.8, 25.8),
                 (-79.6, 29), (-76.5, 33), (-74.5, 35.8), (-68, 38.5), (-58, 40.5),
                 (-48, 42), (-43, 46), (-38, 50), (-28, 52.5), (-18, 54.5), (-11, 57),
                 (-6, 60), (0, 62.5), (6, 65.5), (10, 69), (5, 72.5), (-1.5, 74.3)], False),
    ("surface", [(-30, 52.8), (-34, 56.5), (-38, 59.5), (-42.5, 58.8), (-47, 59.8),
                 (-52, 60.5), (-55, 59), (-53.6, 57.6)], False),
    ("surface", [(62, 8.5), (60.3, 3.5), (58.6, -2.5), (57.5, -8), (56.8, -11.5), (55.8, -14),
                 (54, -15.4)], False),
    ("deep", [(-2, 74.3), (-9, 71.5), (-15, 69), (-26, 66), (-33, 62), (-41, 58.6),
              (-47.5, 58.3), (-53.5, 57.4), (-54, 53.5), (-50, 49), (-50, 43), (-60, 40.2),
              (-68, 37.8), (-73, 33), (-74, 27), (-68, 20.5), (-66, 19.8), (-62.5, 18.9), (-59, 14),
              (-51, 8), (-43, 2),
              (-33.5, -5), (-34, -12), (-35, -17), (-37, -20), (-42, -28), (-48, -36), (-50, -44),
              (-42, -51), (-22, -53), (0, -51), (20, -50), (40, -50), (60, -51), (80, -52),
              (100, -52), (120, -53), (140, -55), (160, -57), (178, -56), (-172, -48),
              (-172, -38), (-172, -28), (-169, -18), (-169, -8), (-172, 5), (-178, 18),
              (174, 30), (166, 37), (162.3, 39.6)], False),
    ("deep", [(40, -50), (47, -41), (54, -31), (60, -21), (64.5, -11), (66, -1), (65, 5),
              (63, 8.2)], False),
    ("bottom", [(-50, -73.3), (-46, -68), (-40, -60), (-39.5, -55), (-44, -47), (-42, -39),
                (-38, -31), (-33, -21), (-29, -11), (-27, -1), (-32, 8), (-42, 16)], True),
    ("bottom", [(172.5, -77.3), (177, -72), (-175, -66), (-172, -58), (-178.5, -46),
                (-177, -36), (-173.5, -24), (-174, -15.5), (-173, -5), (-177, 5), (178, 15),
                (170, 25)], True),
    ("bottom", [(69, -67.3), (64, -62), (58, -56), (56, -48), (58, -40), (56, -32)], True),
    ("bottom", [(140, -66.3), (135, -62), (125, -56), (115, -50), (108, -42), (104, -32),
                (100, -22)], True),
]
# Where water sinks (a surface line ends and a deep or bottom line starts) and where a drawn
# deep limb ends and its water rises (a surface line starts).
MARKS = [("sink", -2, 74.5), ("sink", -53.5, 57.5), ("sink", -50, -73.5),
         ("sink", 172, -77.5), ("sink", 69, -67.6), ("sink", 140, -66.6),
         ("rise", 162, 40), ("rise", 62.5, 8.5)]


def km(lon1, lat1, lon2, lat2):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    a = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(np.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6371 * np.arcsin(np.sqrt(a))


def smooth_path(points, step=60.0):
    """Catmull-Rom curve through the waypoints, one point about every `step` km."""
    lon = np.unwrap(np.radians([p[0] for p in points])) * 180 / np.pi
    p = np.column_stack([lon, [q[1] for q in points]])
    p = np.vstack([2 * p[0] - p[1], p, 2 * p[-1] - p[-2]])
    out = []
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        n = max(2, int(km(p1[0], p1[1], p2[0], p2[1]) / step))
        for t in np.arange(n) / n:
            out.append(0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t ** 2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(p[-2])
    return [[round(float((x + 180) % 360 - 180), 2), round(float(y), 2)] for x, y in out]


def overturning(v, lat, dlon, thickness, mask, smooth_rows):
    """Meridional overturning streamfunction, Sv, at the bottom of each level (surface first):
    the northward transport above that depth across the masked longitudes. The net flow across
    each latitude is removed (spread over the wet section), and the result smoothed over
    `smooth_rows` rows of latitude."""
    dx = dlon * 6.371e6 * np.cos(np.radians(lat))[:, None]
    wet = np.isfinite(v) & mask[None]
    transport = np.nansum(np.where(wet, v, 0) * dx[None], 2) * thickness[:, None] / 1e6
    area = (wet * dx[None]).sum(2) * thickness[:, None]
    transport -= transport.sum(0) * area / np.maximum(area.sum(0), 1)
    psi = np.cumsum(transport, 0)
    psi = uniform_filter1d(psi, smooth_rows, axis=1, mode="nearest")
    psi[area == 0] = np.nan
    return psi


def section(key, lat, depth, psi, lat_range):
    """One panel for the page: psi on its grid plus contours every 4 Sv, each oriented along the
    flow (northward where psi grows with depth, downward where it falls northward)."""
    keep = (lat >= lat_range[0]) & (lat <= lat_range[1])
    lat, psi = lat[keep], psi[:, keep]
    grid = np.nan_to_num(psi)
    dpsi_dd, dpsi_dy = np.gradient(grid)
    contours = []
    for level in [x for x in range(-40, 41, 4) if x]:
        for c in measure.find_contours(grid, level):
            if len(c) < 6:
                continue
            i, j = c[len(c) // 2].round().astype(int)
            flow = np.array([-dpsi_dy[i, j], dpsi_dd[i, j]])   # (d depth, d lat) along the flow
            if np.dot(flow, c[len(c) // 2 + 1] - c[len(c) // 2 - 1]) < 0:
                c = c[::-1]
            pts = [[round(float(np.interp(y, np.arange(lat.size), lat)), 2),
                    round(float(np.interp(x, np.arange(depth.size), depth)))] for x, y in c[::2]]
            contours.append({"level": level, "points": pts})
    return {"basin": key, "lat": [round(float(x), 2) for x in lat], "depth": [round(float(d)) for d in depth],
            "psi": [[None if not np.isfinite(x) else round(float(x), 1) for x in row] for row in psi],
            "contours": contours,
            # The deep cells, leaving out the shallow tropical cells near the surface: the
            # strongest clockwise cell below 300 m and anticlockwise cell below 1 km.
            "red": round(float(np.nanmax(np.where(depth[:, None] >= 300, psi, np.nan))), 1),
            "blue": round(float(-np.nanmin(np.where(depth[:, None] >= 1000, psi, np.nan))), 1)}


def sections(paths):
    v = None
    for path in paths:
        data = netCDF4.Dataset(path)
        a = np.ma.filled(data["vcur"][:].astype(float).mean(0), np.nan)
        v = a if v is None else v + a
    v /= len(paths)
    level = data["level"][:].astype(float)
    edges = np.concatenate([[0], (level[1:] + level[:-1]) / 2, [level[-1] + (level[-1] - level[-2]) / 2]])
    lat, lon = data["lat"][:].astype(float), data["lon"][:].astype(float)
    basins, _ = ndimage.label(np.isfinite(v[0]) & (lat[:, None] > -32))
    basin = lambda lo, la: basins == basins[np.abs(lat - la).argmin(), np.abs(lon - lo % 360).argmin()]
    out = []
    for key, mask in (("atlantic", basin(-30, 0)), ("indopacific", basin(-150, 0) | basin(80, -10))):
        psi = overturning(v, lat, np.radians(1), np.diff(edges), mask, 9)
        out.append(section(key, lat, edges[1:], psi, (-32, 65)))
    return out


def on_land(points, z):
    """The points that fall on the grid's land (z >= 0). The grids are node-registered, rows
    north to south and columns -180 to 180."""
    rows, cols = z.shape
    land = []
    for lon, lat in points:
        r = int(round((90 - lat) / 180 * (rows - 1)))
        c = int(round((lon + 180) / 360 * (cols - 1)))
        if z[r, c] >= 0:
            land.append((lon, lat))
    return land


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", default=OUT, type=Path)
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text())
    paths = [ROOT / asset["path"] for asset in manifest["assets"]]
    missing = [path for path in paths if not path.exists()]
    if missing:
        raise SystemExit(f"Missing {len(missing)} GODAS files; run scripts/fetch_paleodem.py --manifest "
                         f"{MANIFEST.relative_to(ROOT)}")
    lines = [{"kind": kind, "fade": fade, "points": smooth_path(points)} for kind, points, fade in CONVEYOR]
    catalogue = json.loads(CATALOGUE.read_text())
    present = next(item for item in catalogue["maps"] if item["age_ma"] == 0)
    z = elevation(locate(default_source(catalogue), present))
    land = [p for line in lines for p in on_land(line["points"], z)] + on_land([m[1:] for m in MARKS], z)
    if land:
        raise SystemExit(f"{len(land)} schematic points on the present grid's land, e.g. {land[:3]}")
    out = {"source": manifest["cite"], "license": manifest["license"], "record": manifest["record"],
           "lines": lines, "marks": [list(m) for m in MARKS], "sections": sections(paths)}
    (args.out / "circulation.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    size = (args.out / "circulation.json").stat().st_size
    points = sum(len(line["points"]) for line in lines)
    print(f"{len(lines)} lines ({points} points, all at sea), {len(MARKS)} marks; "
          + "; ".join(f"{s['basin']} red {s['red']} / blue {s['blue']} Sv" for s in out["sections"])
          + f"; {size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
