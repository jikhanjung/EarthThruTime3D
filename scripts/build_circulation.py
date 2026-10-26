"""The present-day circulation schematic and overturning sections (wwolf P02 step 5).

Two parts, one file for the page:

- The schematic: the textbook "conveyor belt" drawn from the literature, not traced from data
  (Broecker 1991, doi:10.5670/oceanog.1991.07; Rahmstorf 2002, doi:10.1038/nature01090). The
  warm upper limb runs from where the textbook belt has deep water rise in the North Pacific,
  through the Indonesian passages, round South Africa and up the Atlantic to the Nordic and
  Labrador Seas; the textbook belt also has deep water rise in the northern Indian Ocean,
  drawn here returning south into it as the Indian Ocean's shallow cell does (Schott et al.
  2002, doi:10.1016/S0079-6611(02)00039-3, for the southward return only). North Atlantic Deep
  Water runs from where it sinks south along the Americas, east with the circumpolar current
  and north into the Indian and Pacific Oceans. Antarctic Bottom Water, mostly the cold, salty
  water left when sea ice freezes (ice shelves take part in the Weddell and Ross Seas), runs
  from the Weddell and Ross Seas, the Adelie coast and Cape Darnley (Orsi et al. 1999,
  doi:10.1016/S0079-6611(99)00004-X; Ohshima et al. 2013, doi:10.1038/ngeo1738) north along
  the sea floor under the deep water, and fades out: it mixes upward as it spreads, with no
  single end. Most deep water actually rises in the Southern Ocean, slowly and over a wide
  area (Marshall & Speer 2012, doi:10.1038/ngeo1391), which no line can show.
- The sections: the Atlantic and Indo-Pacific overturning streamfunction north of 32 S from
  the NCEP GODAS reanalysis, 2016-2020 mean (sources/godas.json), the data behind the picture,
  with their numbers read at stated latitudes (READINGS).

The build stops if any line crosses the present's land or ice (every 5 km, on the 6-minute
grid and the present ice mask), or if a line other than the bottom water ends away from a
mark or another line. Writes data/derived/paleodem/circulation.json.
"""
import argparse
import json
import sys
from pathlib import Path

import netCDF4
import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.ndimage import uniform_filter1d
from skimage import measure

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_mountain_ranges import distance_km  # noqa: E402
from scripts.build_paleodem import CATALOGUE, default_source, elevation, locate  # noqa: E402

MANIFEST = ROOT / "sources/godas.json"
OUT = ROOT / "data/derived/paleodem"

# (layer, waypoints (lon, lat), fades out). Smoothed into curves by smooth_path.
CONVEYOR = [
    # Warm upper limb: North Pacific -> Indonesian passages -> Indian Ocean -> round South Africa
    # -> up the Atlantic and the Gulf Stream -> Nordic Seas.
    ("surface", [(162, 40), (159, 33), (155, 25), (148, 16.75), (139, 10), (133, 6), (126.75, 3),
                 (121, 1.5), (119.7, 1), (118.8, -0.5), (118.3, -3.5), (118.2, -4.6), (118.7, -5.6),
                 (119.2, -6.4), (119.1, -7.5), (117.8, -8), (116.3, -8), (115.8, -8.35), (115.75, -8.5),
                 (115.7, -8.7), (115.7, -9.2), (115.1, -10), (111, -13), (95, -14), (75, -15),
                 (62, -14.8), (57, -14.6), (54, -15.5), (51.3, -14.3), (50.3, -11.4),
                 (47.5, -12.2), (45.4, -13.6), (43, -14), (41, -19), (36, -26), (31, -31),
                 (25, -36), (18, -37), (12, -31), (5, -22), (-5, -14), (-18, -9),
                 (-31, -5), (-40, 0), (-48, 4), (-56, 9), (-64.25, 13.5), (-75, 15),
                 (-83, 18.5), (-86, 22.5), (-86, 25.5), (-82.5, 24.2), (-81, 24.25), (-79.95, 24.9),
                 (-79.8, 25.8),
                 (-79.6, 29), (-76.5, 33), (-74.5, 35.55), (-68, 38.5), (-58, 40.5),
                 (-48, 42), (-43, 46), (-38, 50), (-28, 52.5), (-18, 54.5), (-11, 57),
                 (-6, 60), (0, 62.5), (6, 65.5), (10, 69), (5, 72.5), (-1.5, 74.3)], False),
    # Its Labrador Sea branch.
    ("surface", [(-30, 52.8), (-34, 56.5), (-38, 59.5), (-42.5, 58.8), (-47, 59.8),
                 (-52, 60.5), (-55, 59), (-53.6, 57.6)], False),
    # The Arabian Sea connector: from the Arabian Sea southward into the westward flow at 15 S.
    ("surface", [(62, 8.5), (60.3, 3.5), (58.6, -2.5), (57.5, -8), (56.8, -11.5), (55.8, -14),
                 (54, -15.4)], False),
    # North Atlantic Deep Water: Nordic Seas -> south along the Americas -> east with the
    # circumpolar current -> north into the Pacific.
    ("deep", [(-2, 74.3), (-9, 71.5), (-15, 69), (-26, 66), (-33, 62), (-41, 58.6),
              (-47.5, 58.3), (-53.5, 57.4), (-54, 53.5), (-50, 49), (-50, 42.5), (-60, 40.2),
              (-68, 37.8), (-73, 33), (-74, 27), (-68, 20.5), (-66, 19.8), (-62.5, 18.9), (-59, 14),
              (-51, 8), (-43, 2),
              (-33.5, -5), (-34, -12), (-35, -17), (-37, -20), (-42, -28), (-48, -36), (-50, -44),
              (-42, -51), (-22, -53), (0, -51), (20, -50), (40, -50), (60, -51), (80, -52),
              (100, -52), (120, -53), (140, -55), (160, -57), (178, -56), (-172, -48),
              (-172, -38), (-172, -28), (-169, -18), (-169, -8), (-172, 5), (-178, 18),
              (174, 30), (166, 37), (162.3, 39.6)], False),
    # Its branch north into the Indian Ocean.
    ("deep", [(40, -50), (47, -41), (54, -31), (60, -21), (64.5, -11), (66, -1), (65, 5),
              (63, 8.2)], False),
    # Antarctic Bottom Water from the Weddell Sea, north along the Atlantic floor.
    ("bottom", [(-50, -73.3), (-46, -68), (-40, -60), (-39.5, -55), (-44, -47), (-42, -39),
                (-38, -31), (-33, -21), (-29, -11), (-27, -1), (-32, 8), (-42, 16)], True),
    # From the Ross Sea, north along the Pacific floor east of New Zealand.
    ("bottom", [(172.5, -77.3), (177, -72), (-175, -66), (-172, -58), (-178.5, -46),
                (-177, -36), (-173.5, -24), (-174, -15.5), (-173, -5), (-177, 5), (178, 15),
                (170, 25)], True),
    # From Cape Darnley, into the western Indian Ocean.
    ("bottom", [(69, -67.3), (64, -62), (58, -56), (56, -48), (58, -40), (56, -32)], True),
    # From the Adelie coast, into the eastern Indian Ocean.
    ("bottom", [(140, -66.3), (135, -62), (125, -56), (115, -50), (108, -42), (104, -32),
                (100, -22)], True),
]
# Where water sinks into the deep or bottom water (in the Nordic and Labrador Seas a surface
# line ends there; around Antarctica a bottom line starts) and where a drawn deep limb ends
# and its water rises back to the surface (a surface line starts).
MARKS = [("sink", -2, 74.5), ("sink", -53.5, 57.5), ("sink", -50, -73.5),
         ("sink", 172, -77.5), ("sink", 69, -67.6), ("sink", 140, -66.6),
         ("rise", 162, 40), ("rise", 62.5, 8.5)]
# The literature the schematic is drawn after, for the file's provenance.
SCHEMATIC_AFTER = ["10.5670/oceanog.1991.07", "10.1038/nature01090", "10.1016/S0079-6611(99)00004-X",
                   "10.1038/ngeo1738", "10.1016/S0079-6611(02)00039-3", "10.1038/ngeo1391"]


def smooth_path(points, step=60.0):
    """Catmull-Rom curve through the waypoints, one point about every `step` km."""
    lon = np.unwrap(np.radians([p[0] for p in points])) * 180 / np.pi
    p = np.column_stack([lon, [q[1] for q in points]])
    p = np.vstack([2 * p[0] - p[1], p, 2 * p[-1] - p[-2]])
    out = []
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        n = max(2, int(distance_km(p1[0], p1[1], p2[0], p2[1]) / step))
        for t in np.arange(n) / n:
            out.append(0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t ** 2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(p[-2])
    return [[round(float((x + 180) % 360 - 180), 2), round(float(y), 2)] for x, y in out]


def overturning(v, lat, dlon, thickness, mask, smooth_rows):
    """Meridional overturning streamfunction, Sv, at the bottom of each level (surface first):
    the northward transport above that depth across the masked longitudes. The net flow across
    each latitude is removed (spread over the wet section), and the result smoothed over
    `smooth_rows` rows of latitude, counting only rows inside the basin so its edges are not
    pulled toward the zeros beyond them."""
    dx = dlon * 6.371e6 * np.cos(np.radians(lat))[:, None]
    wet = np.isfinite(v) & mask[None]
    transport = np.nansum(np.where(wet, v, 0) * dx[None], 2) * thickness[:, None] / 1e6
    area = (wet * dx[None]).sum(2) * thickness[:, None]
    transport -= transport.sum(0) * area / np.maximum(area.sum(0), 1)
    psi = np.cumsum(transport, 0)
    inside = (area > 0).astype(float)
    weight = uniform_filter1d(inside, smooth_rows, axis=1, mode="nearest")
    psi = uniform_filter1d(psi * inside, smooth_rows, axis=1, mode="nearest") / np.maximum(weight, 1e-9)
    psi[area == 0] = np.nan
    return psi


# Where each section's numbers are read, not its extremes: GODAS has strong deep cells at the
# equator that are doubtful, and the extremes land there. The Atlantic's upper cell at
# 26.5 N, where the RAPID array measures it (17.0 Sv over 2004-2023, McCarthy et al. 2025,
# doi:10.1029/2025GL115055); the bottom water where it enters each basin, at 30 S, as the
# northward flow below 2 km. The Indo-Pacific has no northern sinking, so no red number.
READINGS = {"atlantic": {"red": 26.5, "blue": -30.0}, "indopacific": {"blue": -30.0}}


def reading(colour, at, lat, depth, psi):
    column = psi[:, np.abs(lat - at).argmin()]
    if colour == "red":
        value, row = np.nanmax(np.where(depth >= 300, column, np.nan)), np.nanargmax(np.where(depth >= 300, column, np.nan))
    else:
        deep = np.where(depth >= 2000, column, np.nan)
        value, row = -np.nanmin(deep), np.nanargmin(deep)
    return {"lat": at, "depth": round(float(depth[row])), "sv": round(float(value), 1)}


def section(key, lat, depth, psi):
    """One panel for the page: psi on its grid plus contours every 4 Sv, each oriented along the
    flow (northward where psi grows with depth, downward where it falls northward), and the
    numbers read where READINGS says. Latitudes without any data are left off its edges."""
    keep = np.isfinite(psi).any(0)
    keep[: keep.argmax()] = False
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
            pts = [[round(float(np.interp(col, np.arange(lat.size), lat)), 2),
                    round(float(np.interp(row, np.arange(depth.size), depth)))] for row, col in c[::2]]
            contours.append({"level": level, "points": pts})
    out = {"basin": key, "lat": [round(float(x), 2) for x in lat], "depth": [round(float(d)) for d in depth],
           "psi": [[None if not np.isfinite(x) else round(float(x), 1) for x in row] for row in psi],
           "contours": contours}
    for colour, at in READINGS[key].items():
        out[colour] = reading(colour, at, lat, depth, psi)
    return out


def periodic_labels(wet):
    """Connected regions of `wet`, joined across the first and last columns: GODAS runs from
    1 to 360 E, so its edge is the Greenwich meridian, which the Atlantic crosses."""
    labels, count = ndimage.label(wet)
    root = np.arange(count + 1)
    def find(a):
        while root[a] != a:
            a = root[a]
        return a
    for a, b in zip(labels[:, 0], labels[:, -1]):
        if a and b:
            root[find(a)] = find(b)
    return np.array([find(a) for a in range(count + 1)])[labels]


SOUTH_EDGE = -32   # south of this the oceans join around Antarctica and no basin can be told apart


def sections(paths):
    v, coords = None, None
    for path in paths:
        with netCDF4.Dataset(path) as data:
            grid = tuple(np.asarray(data[name][:], float) for name in ("level", "lat", "lon"))
            if coords is not None and not all(np.array_equal(a, b) for a, b in zip(grid, coords)):
                raise SystemExit(f"{path.name} is on a different grid from the other GODAS years")
            coords = grid
            a = np.ma.filled(data["vcur"][:].astype(float).mean(0), np.nan)
        v = a if v is None else v + a
    v /= len(paths)
    level, lat, lon = coords
    step = np.diff(lon)
    if not np.allclose(step, step[0]):
        raise SystemExit("GODAS longitudes are not evenly spaced")
    edges = np.concatenate([[0], (level[1:] + level[:-1]) / 2, [level[-1] + (level[-1] - level[-2]) / 2]])
    basins = periodic_labels(np.isfinite(v[0]) & (lat[:, None] > SOUTH_EDGE))
    label = lambda lo, la: basins[np.abs(lat - la).argmin(), np.abs(lon - lo % 360).argmin()]
    atlantic, pacific, indian = label(-30, 0), label(-150, 0), label(80, -10)
    if 0 in (atlantic, pacific, indian) or atlantic in (pacific, indian):
        raise SystemExit("a basin seed is on land, or the Atlantic joins the Indo-Pacific")
    # The Atlantic must reach across Greenwich (the Gulf of Guinea, the Norwegian Sea).
    if label(5, -15) != atlantic or label(2, 62) != atlantic:
        raise SystemExit("the Atlantic mask stops at Greenwich")
    smooth_rows = max(1, round(3 / abs(lat[1] - lat[0])))   # 3 degrees of latitude
    out = []
    for key, mask in (("atlantic", basins == atlantic), ("indopacific", (basins == pacific) | (basins == indian))):
        psi = overturning(v, lat, np.radians(step[0]), np.diff(edges), mask, smooth_rows)
        out.append(section(key, lat, edges[1:], psi))
    return out


def at_index(lon, lat, rows, cols, node):
    """Row and column of a point on a grid north first from -180: node-registered (the
    elevation grids) or cell-centred (the textures)."""
    if node:
        # -180 and 180 are the same meridian; the grid's -180 column carries spurious zeros.
        col = int(round((lon + 180) / 360 * (cols - 1)))
        return int(round((90 - lat) / 180 * (rows - 1))), cols - 1 if col == 0 else col
    return min(int((90 - lat) / 180 * rows), rows - 1), min(int((lon + 180) / 360 * cols), cols - 1)


def on_land(points, z, ice):
    """The points on the present's land or ice: the grid at or above 0 m, or the ice mask's
    grounded (red) or floating shelf (green) ice, since under Antarctica the grid is bedrock.
    Each step between two points is sampled every 5 km, not only its ends."""
    dense = []
    for (lon1, lat1), (lon2, lat2) in zip(points, points[1:] or points):
        steps = max(1, int(distance_km(lon1, lat1, lon2, lat2) / 5))
        east = ((lon2 - lon1 + 540) % 360) - 180
        dense += [(((lon1 + east * t + 540) % 360) - 180, lat1 + (lat2 - lat1) * t) for t in np.arange(steps) / steps]
    dense.append(tuple(points[-1]))
    land = []
    for lon, lat in dense:
        r, c = at_index(lon, lat, *z.shape, True)
        i, j = at_index(lon, lat, *ice.shape[:2], False)
        if z[r, c] >= 0 or ice[i, j, 0] >= 128 or ice[i, j, 1] >= 128:
            land.append((round(float(lon), 2), round(float(lat), 2)))
    return land


def loose_ends(lines, marks, tolerance_km=150):
    """Ends of the lines that neither reach a mark nor touch another line: every line but the
    fading bottom water starts and ends where its water comes from or goes to."""
    loose = []
    for i, line in enumerate(lines):
        ends = [line["points"][0]] + ([] if line["fade"] else [line["points"][-1]])
        for lon, lat in ends:
            near_mark = any(distance_km(lon, lat, m[1], m[2]) < tolerance_km for m in marks)
            others = np.array([p for k, other in enumerate(lines) if k != i for p in other["points"]])
            near_line = distance_km(lon, lat, others[:, 0], others[:, 1]).min() < tolerance_km
            if not (near_mark or near_line):
                loose.append((lon, lat))
    return loose


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
    if z.shape != (1801, 3601):
        raise SystemExit("The land check needs the 6-minute PaleoDEM grids (scripts/fetch_paleodem.py); "
                         f"found a {z.shape[1] - 1}-column grid")
    ice_path = args.out / "paleodem-0000-ice.png"
    if not ice_path.exists():
        raise SystemExit(f"Missing {ice_path.name}; run scripts/build_ice.py first")
    ice = np.asarray(Image.open(ice_path).convert("RGB"))
    land = [p for line in lines for p in on_land(line["points"], z, ice)] + \
        [p for m in MARKS for p in on_land([m[1:]], z, ice)]
    if land:
        raise SystemExit(f"{len(land)} schematic points on the present's land or ice, e.g. {land[:3]}")
    loose = loose_ends(lines, MARKS)
    if loose:
        raise SystemExit(f"{len(loose)} line ends reach neither a mark nor another line, e.g. {loose[:3]}")
    out = {"schematic": {"after": [doi for doi in SCHEMATIC_AFTER], "license": "CC BY 4.0",
                         "lines": lines, "marks": [list(m) for m in MARKS]},
           "sections": {"source": manifest["cite"], "license": manifest["license"], "record": manifest["record"],
                        "basins": sections(paths)}}
    text = json.dumps(out, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    (args.out / "circulation.json").write_text(text)
    points = sum(len(line["points"]) for line in lines)
    print(f"{len(lines)} lines ({points} points, every 5 km between them at sea and off ice), {len(MARKS)} marks; "
          + "; ".join(f"{s['basin']} " + ", ".join(f"{c} {s[c]['sv']} Sv at {s[c]['lat']} / {s[c]['depth']} m"
                                                  for c in ("red", "blue") if c in s)
                      for s in out["sections"]["basins"])
          + f"; {len(text.encode()) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
