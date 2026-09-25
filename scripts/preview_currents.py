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
