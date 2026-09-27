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
import re
import sys
from pathlib import Path

import netCDF4
import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.ndimage import gaussian_filter, uniform_filter1d
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
                 (62, -15.5), (54, -15.5), (51.3, -14.3), (50.3, -11.4),
                 (47.5, -12.2), (43, -14), (41, -19), (36, -26), (31, -31),
                 (25, -36), (18, -37), (12, -31), (5, -22), (-5, -14), (-18, -9),
                 (-31, -5), (-40, 0), (-48, 4), (-56, 9), (-64, 13.5), (-75, 15),
                 (-83, 18.5), (-86, 22.5), (-86, 25.5), (-82.5, 24.2), (-79.8, 25.8),
                 (-79.6, 29), (-76.5, 33), (-74.5, 35.8), (-68, 38.5), (-58, 40.5),
                 (-48, 42), (-43, 46), (-38, 50), (-28, 52.5), (-18, 54.5), (-11, 57),
                 (-6, 60), (0, 62.5), (6, 65.5), (10, 69), (5, 72.5), (-1.5, 74.3)]),
    ("surface", [(-30, 52.8), (-34, 56.5), (-38, 59.5), (-42.5, 58.8), (-47, 59.8),
                 (-52, 60.5), (-55, 59), (-53.6, 57.6)]),
    ("surface", [(62, 8.5), (60.3, 3.5), (58.6, -2.5), (57.5, -8), (56.8, -11.5), (55.8, -14),
                 (54, -15.4)]),
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


FOAM_AGES = (20, 40, 60, 80, 100)


def fill_map(age):
    """Where the model's deep water spreads: the positions below 1 km of particles released
    under FOAM's deep-convection sites and followed for 2000 years through its 3-D annual-mean
    flow with its own tracer mixing (4000 m2/s; the scratch tracker track3d.py writes
    track<age>.npy), binned per degree and smoothed. Red where the water came from northern
    sites, blue from southern, purple where both; opacity by how often particles were there.
    Rows north to south, columns -180..180, like the current fields."""
    t = np.load(SCRATCH / f"track{age}.npy")
    north = t[0, :, 1] > 0
    density = []
    for chosen in (north, ~north):
        p = t[:, chosen].reshape(-1, 3)
        p = p[p[:, 2] > 1000]
        h, _, _ = np.histogram2d(p[:, 1], (p[:, 0] + 180) % 360 - 180, bins=[180, 360], range=[[-90, 90], [-180, 180]])
        h = gaussian_filter(np.log1p(h[::-1]), 1.2, mode=("nearest", "wrap"))
        density.append(h / h.max() if h.max() > 0 else h)
    n, s = density
    share = n / np.maximum(n + s, 1e-9)
    red, blue = np.array([214, 96, 77]), np.array([67, 147, 195])
    rgb = share[..., None] * red + (1 - share[..., None]) * blue
    rgba = np.zeros((180, 360, 4), np.uint8)
    rgba[..., :3] = np.round(rgb)
    rgba[..., 3] = np.round(np.clip(np.maximum(n, s), 0, 1) * 0.5 * 255)
    return rgba


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
        marks.append((float(weight.sum()), "model", round(float(lon[j]), 1), round(float(lat[i]), 1)))
    # the four strongest spots in each hemisphere, so a weaker southern source still shows
    marks = [m[1:] for m in sorted(marks, reverse=True)]
    marks = [m for m in marks if m[2] > 0][:4] + [m for m in marks if m[2] <= 0][:4]
    return [panel], marks


# The belt in the past, from the literature and the model together. The literature says where
# deep water formed (static/core/preview-deepwater-data.js); its anchors sit on present coasts
# so a plate can carry them, and they are carried to every PaleoDEM stop from 1 to 110 Ma on
# PALEOMAP's plates, as the page's pins are, then moved to the nearest sea at least 1 km deep
# at that stop: the region a mark stands for is the sea beside the coast. At a FOAM stop the
# model says how water leaves and reaches those places: the fastest routes through its
# annual-mean deep layer (1.5-4 km) away from each source, and through its surface layer
# (0-150 m, above the equatorial undercurrent) toward it, on the model's own grid. A step's time is its length over the flow
# along it, floored at a tenth of the layer's median speed so a route can cross still water.
# Each source takes the sea its routes reach first; the routes form a tree, drawn where a
# branch serves at least 8 % of that sea, each point carrying that share (width and opacity).
# Checked on GODAS 2016-2020 (scratch routes.py): the deep routes from the Labrador and
# Irminger Seas run south along North America, the surface routes to them follow the Gulf
# Stream and the North Brazil Current.
EVIDENCE_SLICES = (0,) + FOAM_AGES
DEEP_SEA_M = -1000.0


def literature_marks():
    text = (ROOT / "static/core/preview-deepwater-data.js").read_text()
    out = {}
    for age in EVIDENCE_SLICES:
        block = re.search(rf"\n  {age}: {{\s*marks: \[(.*?)\n    \]", text, re.S).group(1)
        out[age] = [("warm" if warm else level, float(lon), float(lat)) for level, warm, lon, lat in
                    re.findall(r"level: '(\w+)'(, warm: true)?, at: \[(-?[\d.]+), (-?[\d.]+)\]", block)]
    return out


def great_circle_deg(lon, lat, lon0, lat0):
    a, b = np.radians(lat), np.radians(lat0)
    c = np.sin(a) * np.sin(b) + np.cos(a) * np.cos(b) * np.cos(np.radians(lon - lon0))
    return np.degrees(np.arccos(np.clip(c, -1, 1)))


def evidence_positions():
    """{stop age: [[kind, lon, lat], ...]} for the stop's literature slice (the nearest of 0, 20
    ... 100 Ma, ties to the younger, as the page picks it)."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from assess_pin import PackedModel, Shapes, carried, choose, unit
    from build_paleodem import elevation, locate
    model = PackedModel("paleomap2016"); shapes = Shapes(model)
    marks = literature_marks()
    anchors = sorted({(lon, lat) for list_ in marks.values() for _, lon, lat in list_})
    found = shapes.plates(unit(np.array([a[0] for a in anchors]), np.array([a[1] for a in anchors])))
    plate = {a: choose(f)[0] for a, f in zip(anchors, found)}
    grids = next(p for p in (ROOT / "data/sources/paleodem/nc6").iterdir() if p.is_dir())
    out = {}
    for item in json.loads((ROOT / "sources/paleodem-slices.json").read_text())["maps"]:
        age = float(item["age_ma"])
        if not 1 <= age <= 110:
            continue
        z = elevation(locate(grids, item))[::5, ::5]   # 0.5 degree
        rows, cols = np.nonzero(z < DEEP_SEA_M)
        lats = 90 - rows * 180 / (z.shape[0] - 1); lons = -180 + cols * 360 / (z.shape[1] - 1)
        chosen = min(EVIDENCE_SLICES, key=lambda s: (abs(s - age), s))
        placed = []
        for kind, lon, lat in marks[chosen]:
            at = carried(model, plate[(lon, lat)], (lon, lat), age)
            d = great_circle_deg(lons, lats, at[0], at[1])
            i = d.argmin()
            placed.append([kind, round(float(lons[i]), 2), round(float(lats[i]), 2)])
            if d[i] > 12:
                print(f"  {age:g} Ma: {kind} mark moved {d[i]:.1f} degrees to the sea")
        out[f"{age:g}"] = placed
    return out


def foam_layers(age):
    f = netCDF4.Dataset(SCRATCH / f"{age}_ocean.nc")
    mean = lambda k: np.ma.filled(f[k][:].astype(float).mean(0), np.nan)[::-1]   # top first
    U, V = mean("U"), mean("V")
    z, dz = -f["lev"][:].astype(float)[::-1], f["thickness"][:].astype(float)[::-1]
    lat, lon = f["lat"][:].astype(float), f["lon"][:].astype(float)

    def layer(top, bottom, at):
        pick = (z >= top) & (z <= bottom)
        w = dz[pick][:, None, None] * np.isfinite(U[pick])
        total = np.maximum(w.sum(0), 1e-9)
        return (np.nansum(np.nan_to_num(U[pick]) * w, 0) / total, np.nansum(np.nan_to_num(V[pick]) * w, 0) / total,
                np.isfinite(U[np.abs(z - at).argmin()]))
    return {"deep": layer(1500, 4000, 2000), "surface": layer(0, 150, 0)}, lat, lon


def route_graph(u, v, valid, lat, lon):
    from scipy.sparse import coo_matrix
    ny, nx = valid.shape
    index = np.full(valid.shape, -1); index[valid] = np.arange(valid.sum())
    floor = 0.1 * np.median(np.hypot(u, v)[valid])
    dlat, dlon = np.radians(lat[1] - lat[0]), np.radians(lon[1] - lon[0])
    yy, xx = np.nonzero(valid)
    rows, cols, cost = [], [], []
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if not (dy or dx):
                continue
            y2, x2 = yy + dy, (xx + dx) % nx
            ok = (y2 >= 0) & (y2 < ny)
            y1, x1, y2, x2 = yy[ok], xx[ok], y2[ok], x2[ok]
            ok = valid[y2, x2] & (valid[y2, x1] & valid[y1, x2] if dy and dx else True)   # no corner past land
            y1, x1, y2, x2 = y1[ok], x1[ok], y2[ok], x2[ok]
            ex = 6371e3 * np.cos(np.radians((lat[y1] + lat[y2]) / 2)) * dlon * dx
            ey = 6371e3 * dlat * dy
            length = np.hypot(ex, ey)
            along = ((u[y1, x1] + u[y2, x2]) * ex + (v[y1, x1] + v[y2, x2]) * ey) / (2 * length)
            rows.append(index[y1, x1]); cols.append(index[y2, x2])
            cost.append(length / np.maximum(along, floor))
    n = int(valid.sum())
    return coo_matrix((np.concatenate(cost), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsr(), index


def route_trees(u, v, valid, lat, lon, sources, toward, share_min=0.08):
    """Branches of the fastest-route trees, each running with the flow: away from a source
    (deep) or toward it (surface, toward=True). Points [lon, lat, share of the source's sea]."""
    from scipy.sparse.csgraph import dijkstra
    graph, index = route_graph(u, v, valid, lat, lon)
    yy, xx = np.nonzero(valid)
    starts = []
    for lon0, lat0 in sources:
        d = great_circle_deg(lon[xx], lat[yy], lon0, lat0)
        starts.append(index[yy[d.argmin()], xx[d.argmin()]])
    time, pred = dijkstra(graph.T if toward else graph, indices=starts, return_predecessors=True)
    owner = time.argmin(0)
    lines = []
    for k, start in enumerate(starts):
        mine = (owner == k) & np.isfinite(time[k])
        served = np.where(mine, np.cos(np.radians(lat[yy])), 0.0)
        for c in np.argsort(-np.where(mine, time[k], -1)):
            if mine[c] and c != start:
                served[pred[k, c]] += served[c]
        share = served / served[start]
        branch = mine & (share >= share_min)
        has_child = np.zeros(len(share), bool)
        for c in np.nonzero(branch)[0]:
            if c != start:
                has_child[pred[k, c]] = True
        tips = sorted((c for c in np.nonzero(branch)[0] if not has_child[c] and c != start), key=lambda c: -time[k, c])
        seen = {start}
        for c in tips:
            path = [c]
            while path[-1] not in seen:
                seen.add(path[-1]); path.append(pred[k, path[-1]])
            points = [[float(lon[xx[p]]), float(lat[yy[p]]), float(share[p])] for p in path]
            if len(points) > 2:
                lines.append(route_curve(points if toward else points[::-1]))
    return lines


def route_curve(points, step=60.0):
    """A grid route as a smooth line: a running mean over five cells, ends kept, then a point
    every `step` km with the share interpolated."""
    a = np.array(points)
    a[:, 0] = np.degrees(np.unwrap(np.radians(a[:, 0])))
    if len(a) > 4:
        pad = np.vstack([a[:1]] * 2 + [a] + [a[-1:]] * 2)
        a[1:-1, :2] = np.array([pad[i:i + 5, :2].mean(0) for i in range(1, len(a) - 1)])
    seg = km(a[:-1, 0], a[:-1, 1], a[1:, 0], a[1:, 1])
    s = np.concatenate([[0], np.cumsum(seg)])
    at = np.linspace(0, s[-1], max(2, int(s[-1] / step) + 1))
    x, y, w = (np.interp(at, s, a[:, i]) for i in range(3))
    return [[round(float((xi + 180) % 360 - 180), 2), round(float(yi), 2), round(float(wi), 3)] for xi, yi, wi in zip(x, y, w)]


def routes_foam(age, sources):
    layers, lat, lon = foam_layers(age)
    out = []
    for kind, (u, v, valid) in layers.items():
        for line in route_trees(u, v, valid, lat, lon, sources, toward=kind == "surface"):
            out.append({"kind": kind, "routed": True, "points": line})
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    fields = {"present": drifters(), **{str(age): foam(age) for age in FOAM_AGES}}
    out = {"source": {"present": "NOAA Global Drifter Program 1-degree climatology (Laurindo et al. 2017), CC BY 4.0",
                      **{str(age): f"Pohl, FOAM coupled run at {age} Ma, surface level, annual mean (Zenodo 5780097), CC BY 4.0"
                         for age in FOAM_AGES}}}
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
    conveyor = {
        "present": {"lines": [{"kind": kind, "points": smooth_path(pts), "fade": bool(rest)} for kind, pts, *rest in CONVEYOR],
                    "marks": CONVEYOR_MARKS, "sections": conveyor_present()},
    }
    evidence = evidence_positions()
    conveyor["evidence"] = evidence
    for age in FOAM_AGES:
        panels, marks = conveyor_foam(age)
        sources = [(lon, lat) for _, lon, lat in evidence[f"{age:g}"]]
        conveyor[str(age)] = {"lines": routes_foam(age, sources), "marks": marks, "sections": panels}
        Image.fromarray(fill_map(age)).save(OUT / f"fill-{age}.png")
    (OUT / "conveyor.json").write_text(json.dumps(conveyor, separators=(",", ":"), allow_nan=False))
    for key, c in conveyor.items():
        if key == "evidence":
            continue
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
