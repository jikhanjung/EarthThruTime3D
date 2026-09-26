#!/usr/bin/env python3
"""Preview: current fields and major-current lines for the two current prototypes.

Inputs (scratchpad copies, not pinned): the NOAA Global Drifter Program 1-degree mean
velocity and SST climatology (Laurindo, Mariano & Lumpkin 2017, CC BY 4.0) for the present,
and Pohl's FOAM coupled run at 100 Ma (Zenodo 5780097, CC BY 4.0), its surface level
(-10 m), annual mean of the monthly fields.

Writes static/core/preview-currents/{present,100}.png: 360 x 180, rows north to south,
columns -180..180; red and green the east and north speed, sqrt-encoded over +-2 m/s so
slow water keeps precision (s = sign(u) sqrt(|u|/2), stored as (s+1)/2); blue 255 where
there is a value. And lines.json: for each field the major currents, traced as streamlines
through the fastest water (seeded at the 90th percentile of speed, followed while above the
median, lines kept 450 km apart and 1500 km long or more), each point
[lon, lat, speed m/s, temperature minus the ocean mean at that latitude].
"""
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
SCRATCH = Path(sys.argv[1])
OUT = ROOT / "static/core/preview-currents"
LAT = np.arange(89.5, -90, -1.0)      # row centres, north to south
LON = np.arange(-179.5, 180, 1.0)


def drifters():
    d = netCDF4.Dataset(SCRATCH / "drifter.nc"); d.set_auto_mask(False)
    s = netCDF4.Dataset(SCRATCH / "drifter_sst.nc"); s.set_auto_mask(False)
    lon, lat = d["longitude"][:], d["latitude"][:]
    grid = lambda a: regrid(lon, lat, np.asarray(a, float).T)   # stored lon x lat
    return grid(d["U"][:]), grid(d["V"][:]), grid(s["SST"][:])


def foam(age):
    f = netCDF4.Dataset(SCRATCH / f"{age}_ocean.nc")
    lon, lat = f["lon"][:], f["lat"][:]
    mean = lambda name: np.ma.filled(f[name][:, -1].mean(0), np.nan)   # surface, annual
    lon = np.where(lon > 180, lon - 360, lon)
    order = np.argsort(lon)
    pick = lambda a: regrid(lon[order], lat, a[:, order])
    return pick(mean("U")), pick(mean("V")), pick(mean("TEMP"))


def regrid(lon, lat, a):
    """Nearest source cell for each 1-degree cell (lat x lon source), NaN kept."""
    rows = np.abs(lat[None, :] - LAT[:, None]).argmin(1)
    dlon = np.abs(((lon[None, :] - LON[:, None]) + 180) % 360 - 180)
    cols = dlon.argmin(1)
    out = a[rows][:, cols]
    far = np.abs(lat[rows] - LAT) > 1.5   # beyond the source's latitude range
    out[far] = np.nan
    return out


def encode(u, v):
    ok = np.isfinite(u) & np.isfinite(v)
    e = lambda a: np.round(((np.sign(a) * np.sqrt(np.clip(np.abs(a), 0, 2) / 2)) + 1) / 2 * 255)
    rgba = np.zeros(u.shape + (4,), np.uint8)
    rgba[..., 0] = np.where(ok, e(np.nan_to_num(u)), 128)
    rgba[..., 1] = np.where(ok, e(np.nan_to_num(v)), 128)
    rgba[..., 2] = np.where(ok, 255, 0)
    rgba[..., 3] = 255
    return rgba


def sample(a, lon, lat):
    """Bilinear on the 1-degree grid, longitude wrapping; NaN if any corner is NaN."""
    x = (lon + 179.5) % 360
    y = 89.5 - lat
    if y < 0 or y > 179:
        return np.nan
    x0, y0 = int(np.floor(x)), int(np.floor(y))
    fx, fy = x - x0, y - y0
    x1, y1 = (x0 + 1) % 360, min(y0 + 1, 179)
    return ((1 - fx) * (1 - fy) * a[y0, x0] + fx * (1 - fy) * a[y0, x1]
            + (1 - fx) * fy * a[y1, x0] + fx * fy * a[y1, x1])


def km(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(np.radians, (lon1, lat1, lon2, lat2))
    h = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371 * np.arcsin(np.sqrt(h))


def lines(u, v, t, sep=450.0, step=30.0, min_len=1500.0, max_len=9000.0, seed_q=0.9, keep_q=0.5):
    speed = np.hypot(u, v)
    ocean = np.isfinite(speed)
    seed_min, keep_min = np.nanquantile(speed, seed_q), np.nanquantile(speed, keep_q)
    zonal = np.nanmean(t, 1)
    anomaly = t - zonal[:, None]
    taken = []   # (lon, lat) of every kept point
    def near(lon, lat, d):
        if not taken:
            return False
        pts = np.asarray(taken)
        return (km(lon, lat, pts[:, 0], pts[:, 1]) < d).any()
    def trace(lon, lat, sign):
        out = []
        length = 0.0
        while length < max_len / 2:
            uu, vv = sample(u, lon, lat), sample(v, lon, lat)
            sp = np.hypot(uu, vv)
            if not np.isfinite(sp) or sp < keep_min or abs(lat) > 85:
                break
            # midpoint step along the flow, a fixed distance on the ground
            dlat = sign * vv / sp * step / 111.32
            dlon = sign * uu / sp * step / (111.32 * max(np.cos(np.radians(lat)), 0.05))
            mu, mv = sample(u, lon + dlon / 2, lat + dlat / 2), sample(v, lon + dlon / 2, lat + dlat / 2)
            msp = np.hypot(mu, mv)
            if not np.isfinite(msp) or msp == 0:
                break
            lat += sign * mv / msp * step / 111.32
            lon = (lon + sign * mu / msp * step / (111.32 * max(np.cos(np.radians(lat)), 0.05)) + 180) % 360 - 180
            length += step
            if near(lon, lat, sep / 2):
                break
            out.append((lon, lat))
        return out
    seeds = [(speed[i, j], LON[j], LAT[i]) for i, j in zip(*np.nonzero(ocean & (speed >= seed_min)))]
    kept = []
    for _, lon, lat in sorted(seeds, reverse=True):
        if near(lon, lat, sep):
            continue
        path = trace(lon, lat, -1)[::-1] + [(lon, lat)] + trace(lon, lat, 1)
        if len(path) * step < min_len:
            continue
        pts = path[::2]   # every 60 km
        kept.append([[round(p[0], 2), round(p[1], 2),
                      round(float(np.nan_to_num(sample(speed, *p))), 3),
                      round(float(np.nan_to_num(sample(anomaly, *p))), 2)] for p in pts])
        taken.extend(path)
    return kept


# The conveyor belt, present: a schematic drawn from the textbook pathways (Broecker 1991,
# doi:10.5670/oceanog.1991.07; Rahmstorf 2002, doi:10.1038/nature01090), not traced from
# data. Waypoints (lon, lat), smoothed into curves. "surface": the warm upper limb, from
# where deep water rises in the North Pacific through the Indonesian passages (joined by
# the water rising in the Indian Ocean), round South Africa and up the Atlantic to the
# Nordic and Labrador Seas; "deep": North Atlantic Deep Water from where it sinks, south
# along the Americas, east with the circumpolar current and north into the Indian and
# Pacific Oceans; "bottom": Antarctic Bottom Water from the Weddell and Ross Seas, the Adelie
# coast and Cape Darnley (Orsi et al. 1999, doi:10.1016/S0079-6611(99)00004-X; Ohshima et
# al. 2013, doi:10.1038/ngeo1738), north along the sea floor under the deep water into the
# Atlantic, Pacific and Indian Oceans, marked "fade". Every line starts and ends at a marker
# or on another line; where lines cross they are at different depths.
CONVEYOR = [
    ("surface", [(162, 40), (159, 33), (155, 25), (148, 17), (139, 10), (133, 6), (127, 3.5),
                 (121, 1.5), (118, -2), (115.8, -8.9), (111, -13), (95, -14), (75, -15),
                 (60, -15), (51, -11), (43, -14), (41, -19), (36, -26), (31, -31),
                 (25, -36), (18, -37), (12, -31), (5, -22), (-5, -14), (-18, -9),
                 (-31, -5), (-40, 0), (-48, 4), (-56, 9), (-64, 13.5), (-75, 15),
                 (-83, 18.5), (-86, 22.5), (-86, 25.5), (-82.5, 24.2), (-79.8, 25.8),
                 (-79.6, 29), (-76.5, 33), (-74.5, 35.8), (-68, 38.5), (-58, 40.5),
                 (-48, 42), (-43, 46), (-38, 50), (-28, 52.5), (-18, 54.5), (-11, 57),
                 (-6, 60), (0, 62.5), (6, 65.5), (10, 69), (5, 72.5), (-1.5, 74.3)]),
    ("surface", [(-30, 52.8), (-34, 56.5), (-38, 59.5), (-42.5, 58.8), (-47, 59.8),
                 (-52, 60.5), (-55, 59), (-53.6, 57.6)]),
    ("surface", [(62, 8.5), (58.5, 3.5), (56, -3), (54.5, -9), (54.8, -12.6)]),
    ("deep", [(-2, 74.3), (-9, 71.5), (-15, 69), (-26, 66), (-33, 62), (-41, 58.6),
              (-47.5, 58.3), (-53.5, 57.4), (-54, 53.5), (-50, 49), (-50, 43), (-60, 40.2),
              (-68, 37.8), (-73, 33), (-74, 27), (-68, 20.5), (-59, 14), (-51, 8), (-43, 2),
              (-33.5, -5), (-34, -12), (-37, -20), (-42, -28), (-48, -36), (-50, -44),
              (-42, -51), (-22, -53), (0, -51), (20, -50), (40, -50), (60, -51), (80, -52),
              (100, -52), (120, -53), (140, -55), (160, -57), (178, -56), (-172, -48),
              (-172, -38), (-172, -28), (-169, -18), (-169, -8), (-172, 5), (-178, 18),
              (174, 30), (166, 37), (162.3, 39.6)]),
    ("deep", [(40, -50), (47, -41), (54, -31), (60, -21), (64.5, -11), (66, -1), (65, 5),
              (63, 8.2)]),
    ("bottom", [(-50, -73.3), (-46, -68), (-40, -60), (-37, -55), (-44, -47), (-42, -39),
                (-38, -31), (-33, -21), (-29, -11), (-27, -1), (-32, 8), (-42, 16)], "fade"),
    ("bottom", [(172.5, -77.3), (177, -72), (-175, -66), (-172, -58), (-176, -46),
                (-177, -36), (-173.5, -24), (-174, -15.5), (-173, -5), (-177, 5), (178, 15),
                (170, 25)], "fade"),
    ("bottom", [(69, -67.3), (64, -62), (58, -56), (56, -48), (58, -40), (56, -32)], "fade"),
    ("bottom", [(140, -66.3), (135, -62), (125, -56), (115, -50), (108, -42), (104, -32),
                (100, -22)], "fade"),
]
# Where water sinks (deep water formed; a surface line ends there and a deep or bottom line
# starts) and where a drawn deep limb ends and its water rises (a surface line starts). The
# bottom water has no such end: it mixes upward into the water above as it spreads, drawn
# as a ribbon that fades out.
CONVEYOR_MARKS = [("sink", -2, 74.5), ("sink", -53.5, 57.5), ("sink", -50, -73.5),
                  ("sink", 172, -77.5), ("sink", 69, -67.6), ("sink", 140, -66.6),
                  ("rise", 162, 40), ("rise", 62.5, 8.5)]


def smooth_path(points, step=60.0):
    """Catmull-Rom curve through the waypoints, one point every `step` km."""
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
    the northward transport above that depth across the masked longitudes. The net flow
    across each latitude is removed (spread over the wet section), and the result smoothed
    over `smooth_rows` rows of latitude."""
    dx = dlon * 6.371e6 * np.cos(np.radians(lat))[:, None]
    wet = np.isfinite(v) & mask[None]
    transport = np.nansum(np.where(wet, v, 0) * dx[None], 2) * thickness[:, None] / 1e6
    area = (wet * dx[None]).sum(2) * thickness[:, None]
    transport -= transport.sum(0) * area / np.maximum(area.sum(0), 1)
    psi = np.cumsum(transport, 0)
    psi = uniform_filter1d(psi, smooth_rows, axis=1, mode="nearest")
    psi[area == 0] = np.nan
    return psi


def section(title, lat, depth, psi, lat_range):
    """One panel for the page: psi on its grid plus contours every 4 Sv, each oriented along
    the flow (northward where psi grows with depth, downward where it falls northward)."""
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
    return {"title": title, "lat": [round(float(x), 2) for x in lat], "depth": [round(float(d)) for d in depth],
            "psi": [[None if not np.isfinite(x) else round(float(x), 1) for x in row] for row in psi],
            "contours": contours,
            "max": round(float(np.nanmax(psi)), 1), "min": round(float(np.nanmin(psi)), 1),
            # the deep cells, leaving out the shallow tropical cells near the surface: the
            # strongest clockwise cell below 300 m and anticlockwise cell below 1 km
            "red": round(float(np.nanmax(np.where(depth[:, None] >= 300, psi, np.nan))), 1),
            "blue": round(float(-np.nanmin(np.where(depth[:, None] >= 1000, psi, np.nan))), 1)}


def conveyor_present():
    """GODAS 2016-2020 mean: Atlantic and Indo-Pacific overturning north of 32 S."""
    v = None
    for year in range(2016, 2021):
        f = netCDF4.Dataset(SCRATCH / "godas" / f"vcur.{year}.nc")
        a = np.ma.filled(f["vcur"][:].astype(float).mean(0), np.nan)
        v = a if v is None else v + a
    v /= 5
    level = f["level"][:].astype(float)
    edges = np.concatenate([[0], (level[1:] + level[:-1]) / 2, [level[-1] + (level[-1] - level[-2]) / 2]])
    lat, lon = f["lat"][:].astype(float), f["lon"][:].astype(float)
    ocean = np.isfinite(v[0])
    basins, _ = ndimage.label(ocean & (lat[:, None] > -32))
    basin = lambda lo, la: basins == basins[np.abs(lat - la).argmin(), np.abs(lon - lo % 360).argmin()]
    out = []
    for title, mask in (("대서양", basin(-30, 0)), ("인도양·태평양", basin(-150, 0) | basin(80, -10))):
        psi = overturning(v, lat, np.radians(1), np.diff(edges), mask, 9)
        out.append(section(title, lat, edges[1:], psi, (-32, 65)))
    return out


def conveyor_foam(age):
    """FOAM's global overturning, and where its deep convection is most frequent."""
    f = netCDF4.Dataset(SCRATCH / f"{age}_ocean.nc")
    v = np.ma.filled(f["V"][:].astype(float).mean(0), np.nan)[::-1]
    thickness = f["thickness"][:].astype(float)[::-1]
    lat, lon = f["lat"][:].astype(float), f["lon"][:].astype(float)
    lon = np.where(lon > 180, lon - 360, lon)
    psi = overturning(v, lat, 2 * np.pi / lon.size, thickness, np.isfinite(v[0]), 3)
    panel = section("전 지구", lat, np.cumsum(thickness), psi, (-80, 80))
    convection = np.nan_to_num(np.ma.filled(f["CONVEC2"][:].astype(float).mean(0), 0))
    spots, n = ndimage.label(convection > 50)
    marks = []
    for k in range(1, n + 1):
        cells = spots == k
        weight = convection * cells
        i, j = np.unravel_index(weight.argmax(), weight.shape)
        marks.append((float(weight.sum()), "sink", round(float(lon[j]), 1), round(float(lat[i]), 1)))
    marks = [m[1:] for m in sorted(marks, reverse=True)[:6]]
    return [panel], marks


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    fields = {"present": drifters(), "100": foam(100)}
    out = {"source": {"present": "NOAA Global Drifter Program 1-degree climatology (Laurindo et al. 2017), CC BY 4.0",
                      "100": "Pohl, FOAM coupled run at 100 Ma, surface level, annual mean (Zenodo 5780097), CC BY 4.0"}}
    for key, (u, v, t) in fields.items():
        Image.fromarray(encode(u, v)).save(OUT / f"{key}.png")
        # FOAM's surface carries a broad slow wind drift away from the equator; stricter
        # thresholds keep its lines to the currents proper.
        found = lines(u, v, t, **({} if key == "present" else {"seed_q": 0.95, "keep_q": 0.7}))
        out[key] = found
        sp = np.hypot(u, v)
        print(f"{key}: {np.isfinite(sp).sum()} cells, speed p50 {np.nanquantile(sp, .5):.3f} p90 {np.nanquantile(sp, .9):.3f} m/s; "
              f"{len(found)} lines, {sum(len(l) for l in found)} points")
    # The conveyor mode: the present schematic with GODAS's basin overturning, and at 100 Ma
    # FOAM's surface lines with its deep-convection sites and global overturning.
    panels, marks = conveyor_foam(100)
    conveyor = {
        "present": {"lines": [{"kind": kind, "points": smooth_path(pts), "fade": bool(rest)} for kind, pts, *rest in CONVEYOR],
                    "marks": CONVEYOR_MARKS, "sections": conveyor_present()},
        "100": {"lines": [{"kind": "surface", "points": [p[:2] for p in l]} for l in out["100"]],
                "marks": marks, "sections": panels},
    }
    (OUT / "conveyor.json").write_text(json.dumps(conveyor, separators=(",", ":"), allow_nan=False))
    for key, c in conveyor.items():
        print(f"conveyor {key}: {len(c['lines'])} lines, marks {c['marks']}; sections "
              + ", ".join(f"{s['title']} {s['min']}..{s['max']} Sv, {len(s['contours'])} contours" for s in c["sections"]))
    (OUT / "lines.json").write_text(json.dumps(out, separators=(",", ":"), allow_nan=False))
    # How FOAM's coast matches the PaleoDEM grid of the same age (the grids as build_paleodem
    # reads them, north to south).
    sys.path.insert(0, str(ROOT))
    from scripts.build_paleodem import elevation
    for age in (100,):
        z = elevation(sorted(ROOT.glob(f"data/sources/paleodem/nc6/*/*_{age}Ma.nc"))[0])
        rows = ((90 - LAT) / 180 * (z.shape[0] - 1)).round().astype(int)
        cols = ((LON + 180) / 360 * (z.shape[1] - 1)).round().astype(int)
        dem_ocean = z[rows][:, cols] <= 0
        foam_ocean = np.isfinite(fields[str(age)][0])
        print(f"{age} Ma: FOAM and PaleoDEM agree on land or sea in {np.mean(foam_ocean == dem_ocean):.1%} of cells")

if __name__ == "__main__":
    main()
