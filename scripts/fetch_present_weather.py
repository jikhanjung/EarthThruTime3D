#!/usr/bin/env python3
"""Pin one present-day moment of wind and clouds for a release (jikhanjung P10 §3.2).

Usage: .venv/bin/python scripts/fetch_present_weather.py [--cycle YYYYMMDDHH]

Run in the release PR. Picks the newest NOAA GFS cycle whose analysis (f000) is up on NOMADS
(or --cycle), and at that same hour takes the NOAA/NESDIS GMGSI longwave-IR mosaic, so wind,
model clouds and satellite clouds all show one moment T. Not a live feed: the screen says
when T was and that it was taken when the release was built.

Publishes into data/derived/present-earth/ (section `weather`):
- 10m, 250hPa   RGB 1440x721, R=u, G=v scaled to the ranges in index.json, B=0;
                        longitude from -180, latitude 90 -> -90 (0.25 deg)
- cloud-model   L 1440x721, GFS total cloud cover already turned into opacity
- cloud-sat     L 1800x900 (0.2 deg), GMGSI brightness already turned into opacity;
                        empty beyond +-72.7 deg latitude
The previous moment's files are removed; sources/present_weather.json records what was fetched.

Ported from GSM (koprifossillab 007/008/011/012: `gfs.py`, `gmgsi.py`, `wind.py`). Needs
eccodes (GRIB2) and h5py (HDF5) from requirements-processing.txt.
"""
import argparse
import datetime as dt
import hashlib
import io
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import present_catalogue

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/sources/present"
USER_AGENT = "EarthThruTime3D/1.0 (+https://earththrutime.nopeoplestime.info/about/)"

GFS_FILTER = "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl"
GFS_LEVELS = {"10m": "lev_10_m_above_ground", "250hPa": "lev_250_mb"}
GFS_CREDIT = "NOAA/NCEP GFS 0.25° analysis (public domain)"
GMGSI_BUCKET = "https://noaa-gmgsi-pds.s3.amazonaws.com"
GMGSI_PRODUCT = "GMGSI_LW"
GMGSI_CREDIT = "NOAA/NESDIS GMGSI — geostationary IR mosaic (public domain)"
WIDTH, HEIGHT = 1440, 721
SAT_WIDTH, SAT_HEIGHT = 1800, 900
#: Model cloud fraction -> opacity (GSM `CLOUD_ALPHA`)
CLOUD_ALPHA = (0.9, 0.85)
#: Satellite brightness -> opacity: clear tropical sea ~90, deserts 70-105, cloud 130-255 (GSM koprifossillab 012)
SAT_CLEAR, SAT_FULL = 105, 210
#: The newest sat pixel row is +-72.7 deg; beyond it nothing
SAT_LIMIT = 72.7


def get(url, params=None, timeout=120):
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read(), url
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), url


# ── GFS ────────────────────────────────────────────────────────────

def gfs_params(cycle):
    day, hour = cycle[:8], cycle[8:]
    query = {"dir": f"/gfs.{day}/{hour}/atmos", "file": f"gfs.t{hour}z.pgrb2.0p25.f000",
             "var_UGRD": "on", "var_VGRD": "on", "var_TCDC": "on", "lev_entire_atmosphere": "on"}
    query.update({lev: "on" for lev in GFS_LEVELS.values()})
    return query


def recent_cycles(now, count=4):
    start = now.replace(minute=0, second=0, microsecond=0, hour=now.hour - now.hour % 6)
    return [(start - dt.timedelta(hours=6 * i)).strftime("%Y%m%d%H") for i in range(count)]


def gfs_download(cycle):
    status, body, url = get(GFS_FILTER, gfs_params(cycle))
    if status == 200 and body[:4] == b"GRIB":
        return body, url
    if status == 404:
        return None, url
    raise RuntimeError(f"NOMADS answered {status} for {cycle}")


def grib_messages(grib):
    pos = 0
    while pos + 16 <= len(grib):
        if grib[pos:pos + 4] != b"GRIB":
            raise ValueError(f"no GRIB header at byte {pos}")
        total = int.from_bytes(grib[pos + 8:pos + 16], "big")
        yield grib[pos:pos + total]
        pos += total


def gfs_decode(grib):
    """GRIB2 -> ({level: (u, v)}, total cloud 0-1); grids 721x1440, longitude from 0, latitude from 90."""
    import eccodes
    import numpy as np

    by_level = {"10": "10m", "25000": "250hPa", "250": "250hPa"}
    found, cloud = {}, None
    for msg in grib_messages(grib):
        handle = eccodes.codes_new_from_message(msg)
        try:
            name = eccodes.codes_get(handle, "shortName")
            level = by_level.get(str(eccodes.codes_get(handle, "level")))
            ni, nj = eccodes.codes_get(handle, "Ni"), eccodes.codes_get(handle, "Nj")
            first = (eccodes.codes_get(handle, "latitudeOfFirstGridPointInDegrees"),
                     eccodes.codes_get(handle, "longitudeOfFirstGridPointInDegrees"))
            if (ni, nj) != (WIDTH, HEIGHT) or first != (90, 0):
                raise ValueError(f"unexpected grid {ni}x{nj} from {first}")
            values = np.asarray(eccodes.codes_get_values(handle), dtype=np.float32).reshape(HEIGHT, WIDTH)
            type_of_level = eccodes.codes_get(handle, "typeOfLevel")
            instant = eccodes.codes_get(handle, "stepType") == "instant"
        finally:
            eccodes.codes_release(handle)
        if name == "tcc":
            # TCDC also comes on pressure levels (250 mb rides along); keep the whole column only
            if type_of_level == "atmosphere" and instant:
                cloud = values / 100.0
            continue
        comp = {"u": "u", "10u": "u", "v": "v", "10v": "v"}.get(name)
        if level and comp:
            found.setdefault(level, {})[comp] = values
    fields = {}
    for level in GFS_LEVELS:
        pair = found.get(level, {})
        if "u" not in pair or "v" not in pair:
            raise ValueError(f"{level}: u/v missing")
        fields[level] = (pair["u"], pair["v"])
    if cloud is None:
        raise ValueError("total cloud cover missing")
    return fields, cloud


def png(array, mode):
    from PIL import Image

    out = io.BytesIO()
    Image.fromarray(array, mode).save(out, "PNG", optimize=True)
    return out.getvalue()


def encode_wind(u, v):
    import numpy as np

    u, v = (np.roll(np.asarray(a, dtype=np.float32), WIDTH // 2, axis=1) for a in (u, v))
    if not (np.isfinite(u).all() and np.isfinite(v).all()):
        raise ValueError("NaN in wind")
    rgb = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    scale = {}
    for i, (name, grid) in enumerate((("u", u), ("v", v))):
        lo, hi = float(grid.min()), float(grid.max())
        rgb[..., i] = np.rint((grid - lo) / (hi - lo or 1.0) * 255).astype(np.uint8)
        scale[name] = [round(lo, 3), round(hi, 3)]
    return png(rgb, "RGB"), scale


def encode_model_cloud(fraction):
    import numpy as np

    f = np.roll(np.clip(np.asarray(fraction, dtype=np.float32), 0, 1), WIDTH // 2, axis=1)
    alpha = CLOUD_ALPHA[0] * f ** CLOUD_ALPHA[1]
    return png(np.rint(alpha * 255).astype(np.uint8), "L")


# ── GMGSI ──────────────────────────────────────────────────────────

def gmgsi_key(hour):
    prefix = f"{GMGSI_PRODUCT}/{hour:%Y/%m/%d/%H}/"
    status, body, _ = get(GMGSI_BUCKET + "/", {"list-type": "2", "prefix": prefix, "max-keys": "20"}, timeout=30)
    if status != 200:
        raise RuntimeError(f"GMGSI listing answered {status}")
    keys = sorted(k for k in re.findall(r"<Key>([^<]+)</Key>", body.decode()) if k.endswith(".nc"))
    return keys[-1] if keys else None


def gmgsi_decode(blob):
    """HDF5 Mercator mosaic -> 0.2 deg lat/lon grey grid (900x1800, longitude from -180, latitude from 90)."""
    import h5py
    import numpy as np

    with h5py.File(io.BytesIO(blob), "r") as f:
        data = np.asarray(f["data"][0], dtype=np.float32)
        lat = np.asarray(f["lat"][:, 0], dtype=np.float64)
        lon = np.asarray(f["lon"][0], dtype=np.float64)
    if data.ndim != 2 or data.shape != (lat.size, lon.size):
        raise ValueError(f"unexpected GMGSI grid {data.shape}")
    data = np.where(data < 0, 0, data)
    lon = (lon + 180) % 360 - 180
    order = np.argsort(lon)
    lon, data = lon[order], data[:, order]
    step = 360 / SAT_WIDTH
    want_lon = -180 + step / 2 + step * np.arange(SAT_WIDTH)
    cols = np.clip(np.searchsorted(lon, want_lon), 0, lon.size - 1)
    want_lat = 90 - step / 2 - step * np.arange(SAT_HEIGHT)
    asc = lat[::-1]
    pos = np.interp(want_lat, asc, np.arange(asc.size))
    inside = (want_lat <= asc[-1]) & (want_lat >= asc[0])
    r0 = np.floor(pos).astype(int)
    r1 = np.minimum(r0 + 1, asc.size - 1)
    frac = (pos - r0)[:, None]
    rows = data[::-1]
    grid = rows[r0][:, cols] * (1 - frac) + rows[r1][:, cols] * frac
    grid[~inside] = 0
    return grid


def encode_sat(gray):
    import numpy as np

    f = np.clip((gray - SAT_CLEAR) / (SAT_FULL - SAT_CLEAR), 0, 1)
    return png(np.rint(255 * 0.92 * f ** 0.9).astype(np.uint8), "L")


# ── main ───────────────────────────────────────────────────────────

def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cycle", help="GFS cycle YYYYMMDDHH (default: newest with an analysis)")
    args = parser.parse_args(argv)

    cycles = [args.cycle] if args.cycle else recent_cycles(dt.datetime.now(dt.timezone.utc))
    grib = None
    for cycle in cycles:
        grib, gfs_url = gfs_download(cycle)
        if grib:
            break
        print(f"GFS {cycle}: not up yet", file=sys.stderr)
    if not grib:
        raise SystemExit("no GFS analysis found")
    moment = dt.datetime.strptime(cycle, "%Y%m%d%H").replace(tzinfo=dt.timezone.utc)
    key = gmgsi_key(moment)
    if not key:
        raise SystemExit(f"no GMGSI image for {cycle}")
    status, sat_blob, sat_url = get(f"{GMGSI_BUCKET}/{key}", timeout=300)
    if status != 200 or len(sat_blob) < 1_000_000:
        raise SystemExit(f"GMGSI download failed ({status}, {len(sat_blob)} B)")

    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / f"gfs-{cycle}-f000.grib2").write_bytes(grib)
    (RAW / key.rsplit("/", 1)[-1]).write_bytes(sat_blob)

    fields, cloud = gfs_decode(grib)
    files, ranges = {}, {}
    for level, (u, v) in fields.items():
        files[level], ranges[level] = encode_wind(u, v)
    files["cloud-model"] = encode_model_cloud(cloud)
    files["cloud-sat"] = encode_sat(gmgsi_decode(sat_blob))

    index = {
        "t": moment.strftime("%Y-%m-%dT%H:%MZ"),
        "wind": {"levels": list(GFS_LEVELS), "width": WIDTH, "height": HEIGHT, **ranges},
        "clouds": {"model": {"width": WIDTH, "height": HEIGHT}, "sat": {"width": SAT_WIDTH, "height": SAT_HEIGHT,
                                                                       "limit_deg": SAT_LIMIT}},
        "files": {name: {"bytes": len(blob), "sha256": sha(blob)} for name, blob in files.items()},
        "sources": {
            "gfs": {"url": gfs_url, "bytes": len(grib), "sha256": sha(grib), "credit": GFS_CREDIT},
            "gmgsi": {"url": sat_url, "bytes": len(sat_blob), "sha256": sha(sat_blob), "credit": GMGSI_CREDIT},
        },
        "retrieved": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
    }
    (ROOT / "sources/present_weather.json").write_text(json.dumps(index, ensure_ascii=False, indent=1) + "\n")
    present_catalogue.write_section("weather", {k: (blob, "png") for k, blob in files.items()}, {
        "t": index["t"], "wind": index["wind"], "clouds": index["clouds"],
        "credits": {k: v["credit"] for k, v in index["sources"].items()}})
    print(index["t"])


if __name__ == "__main__":
    main()
