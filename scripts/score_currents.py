"""Score present-day surface currents against the NOAA drifter annual mean (wwolf P02 step 1).

Measures the ECCO2 1992-2018 mean the site draws at 0 Ma (P10, data/derived/present-earth)
and, if given, Pohl's FOAM 0 Ma run against the drifters, with the metric of P02's 0 Ma
table: the drifter 1-degree points whose observed speed is at least 2 cm/s and where every
compared model has a value, weighted by cos(latitude). Prints the direction agreement, the
mean speeds, three named boxes and the five western boundary currents. Writes nothing.

Inputs: the drifter file of sources/drifters.json; the ECCO2 mean through the present-earth
catalogue (scripts/build_ecco2_mean.py); optionally the FOAM 0 Ma ocean file
`0rd_1368W_EccN_ocean_2240ppm.nc` from doi:10.5281/zenodo.5780097 (124,268,380 bytes,
md5 d8479ce51f55cf793d04c1b8524163c7). Recorded results: devlog wwolf 020.
"""
import argparse
import json
from pathlib import Path

import netCDF4
import numpy as np
from PIL import Image
from scipy.interpolate import RegularGridInterpolator

ROOT = Path(__file__).resolve().parents[1]
DRIFTERS = ROOT / "data/sources/currents/drifter_annualmeans_1deg.nc"
CATALOGUE = ROOT / "data/derived/present-earth/catalogue.json"
SLOW = 0.02            # m/s: slower drifter cells carry no usable direction
TROPICS = 15           # degrees either side of the equator

# Named boxes (lat0, lat1, lon0, lon1); the equatorial one wraps the date line.
BOXES = {
    "equatorial Pacific 2S-2N, 160E-100W, u": (-2, 2, 160, -100),
    "Antarctic Circumpolar Current 50-60S, u": (-60, -50, -180, 180),
    "Gulf Stream 35-40N, 75-60W, u": (35, 40, -75, -60),
}
# Western boundary currents: box and the direction the current flows (east, north).
BOUNDARY = {
    "Gulf Stream 35-40N 75-60W": ((35, 40, -75, -60), (1, 0.3)),
    "Kuroshio 30-36N 130-142E": ((30, 36, 130, 142), (1, 0.5)),
    "Brazil 25-38S 55-47W": ((-38, -25, -55, -47), (-0.4, -1)),
    "East Australian 25-35S 150-157E": ((-35, -25, 150, 157), (0, -1)),
    "Agulhas 30-35S 26-31E": ((-35, -30, 26, 31), (-0.8, -0.6)),
}


def drifters(path):
    d = netCDF4.Dataset(path)
    d.set_auto_mask(False)
    lon = np.asarray(d["longitude"][:], float)
    lat = np.asarray(d["latitude"][:], float)
    u = np.asarray(d["U"][:], float).T        # stored longitude x latitude
    v = np.asarray(d["V"][:], float).T
    bad = ~np.isfinite(u) | ~np.isfinite(v) | (np.abs(u) > 50) | (np.abs(v) > 50)
    u[bad] = v[bad] = np.nan
    return np.where(lon > 180, lon - 360, lon), lat, u, v


def ecco2(catalogue, lon, lat):
    """The 1440x720 mean, north first from -180; code -> value linearly over each range."""
    ocean = json.loads(catalogue.read_text())["ocean"]
    rgb = np.asarray(Image.open(catalogue.parent / ocean["assets"]["mean"]["file"]).convert("RGB"), float)
    rows = np.rint((89.875 - lat) / 0.25).astype(int)
    cols = np.rint((lon + 179.875) / 0.25).astype(int) % 1440
    cell = rgb[np.ix_(rows, cols)]
    u, v = (cell[..., i] / 255 * (r[1] - r[0]) + r[0] for i, r in enumerate((ocean["u"], ocean["v"])))
    sea = cell[..., 2] > 127
    u[~sea] = v[~sea] = np.nan
    return u, v


def foam(path, lon, lat):
    """FOAM's top level (-10 m), mean of the 12 months, bilinear onto the drifter points."""
    f = netCDF4.Dataset(path)
    flon = np.asarray(f["lon"][:], float)
    flat = np.asarray(f["lat"][:], float)
    x = np.concatenate([[flon[-1] - 360], flon, [flon[0] + 360]])     # wrap the seam
    points = np.stack(np.meshgrid(lat, np.mod(lon, 360), indexing="ij"), -1)
    out = []
    for name in ("U", "V"):
        a = np.ma.filled(f[name][:, -1].mean(0), np.nan)
        a = np.concatenate([a[:, -1:], a, a[:, :1]], axis=1)
        out.append(RegularGridInterpolator((flat, x), a, bounds_error=False, fill_value=np.nan)(points))
    return out


def in_box(P, L, box):
    lat0, lat1, lon0, lon1 = box
    lon_ok = (L >= lon0) & (L <= lon1) if lon0 <= lon1 else (L >= lon0) | (L <= lon1)
    return (P >= lat0) & (P <= lat1) & lon_ok


def report(models, lon, lat, uo, vo):
    P, L = np.meshgrid(lat, lon, indexing="ij")
    so = np.hypot(uo, vo)
    valid = np.isfinite(uo)
    for u, _ in models.values():
        valid &= np.isfinite(u)
    common = valid & (so >= SLOW)
    w = np.cos(np.radians(P))
    share = lambda hit, m: np.sum(w[m & hit]) / np.sum(w[m]) * 100
    trop = np.abs(P) <= TROPICS
    print(f"{common.sum()} drifter cells of at least {SLOW * 100:.0f} cm/s, weighted by cos(latitude)")
    for name, (u, v) in models.items():
        cosang = (uo * u + vo * v) / (so * np.hypot(u, v) + 1e-12)
        print(f"\n{name}")
        print(f"  within 90°: {share(cosang > 0, common):.0f} %  (outside ±{TROPICS}°: "
              f"{share(cosang > 0, common & ~trop):.0f} %, inside: {share(cosang > 0, common & trop):.0f} %)")
        print(f"  within 45°: {share(cosang > np.cos(np.radians(45)), common):.0f} %")
        print(f"  zonal sign: {share(np.sign(u) == np.sign(uo), common):.0f} %")
        print(f"  mean speed: {np.sum(w[common] * np.hypot(u, v)[common]) / np.sum(w[common]):.3f} m/s, "
              f"drifters {np.sum(w[common] * so[common]) / np.sum(w[common]):.3f} m/s")
        for label, box in BOXES.items():
            m = in_box(P, L, box) & valid
            print(f"  {label}: {np.mean(u[m]):+.3f}, drifters {np.mean(uo[m]):+.3f} m/s")
    print("\nWestern boundary currents: mean along-flow speed in the box, and the share of the box's")
    print("fastest quarter of drifter cells where the model flows within 90° of them")
    for label, (box, (east, north)) in BOUNDARY.items():
        m = in_box(P, L, box) & valid
        norm = np.hypot(east, north)
        along = lambda u, v: np.mean(u[m] * east / norm + v[m] * north / norm)
        fast = m & (so >= np.percentile(so[m], 75))
        line = f"  {label} ({m.sum()} cells, {fast.sum()} fast): drifters {along(uo, vo):+.2f}"
        for name, (u, v) in models.items():
            line += f" | {name} {along(u, v):+.2f}, {np.mean((u[fast] * uo[fast] + v[fast] * vo[fast]) > 0) * 100:.0f} %"
        print(line + " m/s")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--drifters", type=Path, default=DRIFTERS)
    ap.add_argument("--catalogue", type=Path, default=CATALOGUE, help="present-earth catalogue.json")
    ap.add_argument("--foam", type=Path, help="FOAM 0 Ma ocean file (optional)")
    args = ap.parse_args()
    lon, lat, uo, vo = drifters(args.drifters)
    models = {"ECCO2": ecco2(args.catalogue, lon, lat)}
    if args.foam:
        models["FOAM"] = foam(args.foam, lon, lat)
    report(models, lon, lat, uo, vo)


if __name__ == "__main__":
    main()
