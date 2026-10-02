#!/usr/bin/env python3
"""Fetch ECCO2 cube92 surface currents and bake one climatological mean (jikhanjung P10 §3.3).

Usage: .venv/bin/python scripts/build_ecco2_mean.py [--from 1992 --to 2018] [--pause 1] [--bake-only]

Takes, for every month in the range, the 3-day mean nearest the 15th that exists for both UVEL
and VVEL on the NASA NAS portal (no login), reads only the top layer (5 m) of each 207 MB
netCDF-classic file with an HTTP Range request, keeps the raw layer under
data/sources/ecco2/, and averages u and v cell by cell over the sea samples. The mean is a
model climatology, not an observation; eddies average out and the mean flow remains.

Ported from GSM (koprifossillab 014/015, `web/viewer/ecco.py` and `ocean.py`), including its
three fixes: the velocity files are shifted from their header longitudes (u 430 columns,
v 429 columns, both one row), the two southernmost rows carry junk values up to 1e35, and the
portal drops the last byte of large Range responses.

Publishes into data/derived/present-earth/ (section `ocean`): one RGB 1440x720 PNG, R=u,
G=v scaled to the catalogue's ranges, B=255 sea / 0 land; longitude from -180, latitude
89.875 -> -89.875. Resumable: raw layers already on disk are not fetched again.
"""
import argparse
import io
import json
import os
import re
import struct
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

import present_catalogue

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/sources/ecco2"
BASE = "https://data.nas.nasa.gov/ecco/cs_510/"
VARS = ("UVEL", "VVEL")
WIDTH, HEIGHT, DEPTHS = 1440, 720, 50
HEAD_BYTES = 32768
#: Columns and rows the velocity files are shifted from their header (GSM docs/ECCO2_해류_시각화.md §10)
SHIFT = {"UVEL": (430, -1), "VVEL": (429, -1)}
JUNK_ROWS = 2
MAX_SPEED = 3.0
CITATION = ("ECCO2 cube92 (NASA JPL/MIT), Menemenlis, D., et al. (2008), ECCO2: High resolution global "
            "ocean and sea ice data synthesis, Mercator Ocean Quarterly Newsletter 31, 13-21.")
USER_AGENT = "EarthThruTime3D/1.0 (+https://earththrutime.nopeoplestime.info/about/)"


def get(url, byte_range=None, timeout=120):
    headers = {"User-Agent": USER_AGENT}
    want = None
    if byte_range:
        # Ask for one byte more: the portal drops the last byte of large ranges
        headers["Range"] = f"bytes={byte_range[0]}-{byte_range[1] + 1}"
        want = byte_range[1] - byte_range[0] + 1
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status not in (200, 206):
            raise RuntimeError(f"{url}: HTTP {response.status}")
        if want and response.status == 206:
            body = response.read(want)
            if len(body) < want:
                raise RuntimeError(f"{url}: {len(body)} of {want} bytes")
            return body
        return response.read()


_TYPES = {1: 1, 2: 1, 3: 2, 4: 4, 5: 4, 6: 8}


def parse_header(buf):
    """netCDF classic header -> {variable: {"dims": [(name, size)], "type": n, "begin": offset}}."""
    if buf[:3] != b"CDF" or buf[3] not in (1, 2):
        raise ValueError("not netCDF classic")
    wide = buf[3] == 2
    pos = 8

    def u32():
        nonlocal pos
        value = struct.unpack_from(">I", buf, pos)[0]
        pos += 4
        return value

    def name():
        nonlocal pos
        n = u32()
        text = buf[pos:pos + n].decode("utf-8", "replace")
        pos += (n + 3) // 4 * 4
        return text

    def skip_attrs():
        nonlocal pos
        u32()
        for _ in range(u32()):
            name()
            kind, count = u32(), u32()
            pos += (count * _TYPES[kind] + 3) // 4 * 4

    u32()
    dims = [(name(), u32()) for _ in range(u32())]
    skip_attrs()
    u32()
    out = {}
    for _ in range(u32()):
        var = name()
        ids = [u32() for _ in range(u32())]
        skip_attrs()
        kind, _size = u32(), u32()
        begin = struct.unpack_from(">Q", buf, pos)[0] if wide else u32()
        if wide:
            pos += 8
        out[var] = {"dims": [dims[i] for i in ids], "type": kind, "begin": begin}
    return out


def file_url(var, stamp):
    return f"{BASE}{var}.nc/{var}.{WIDTH}x{HEIGHT}x{DEPTHS}.{stamp}.nc"


def listed(var):
    page = get(f"{BASE}{var}.nc/", timeout=60).decode("utf-8", "replace")
    return set(re.findall(rf"{var}\.{WIDTH}x{HEIGHT}x{DEPTHS}\.(\d{{8}})\.nc", page))


def monthly(stamps, first, last):
    """For each month, the stamp nearest the 15th."""
    chosen = []
    for year in range(first, last + 1):
        for month in range(1, 13):
            mid = date(year, month, 15)
            near = [s for s in stamps if s.startswith(f"{year}{month:02d}")]
            if near:
                chosen.append(min(near, key=lambda s: abs((date(int(s[:4]), int(s[4:6]), int(s[6:])) - mid).days)))
    return chosen


def fetch_surface(var, stamp):
    path = RAW / var / f"{stamp}.f4be"
    if path.exists() and path.stat().st_size == WIDTH * HEIGHT * 4:
        return path
    url = file_url(var, stamp)
    spec = parse_header(get(url, (0, HEAD_BYTES - 1), timeout=60)).get(var)
    if not spec or spec["type"] != 5 or [n for _, n in spec["dims"]][-2:] != [HEIGHT, WIDTH]:
        raise ValueError(f"{url}: unexpected variable layout")
    size = WIDTH * HEIGHT * 4
    body = get(url, (spec["begin"], spec["begin"] + size - 1))
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_suffix(".part")
    part.write_bytes(body)
    os.replace(part, path)
    return path


def corrected(var, raw):
    """Raw big-endian layer (south row first, shifted longitudes) -> float grid, NaN on land/junk."""
    import numpy as np

    grid = np.frombuffer(raw, dtype=">f4").reshape(HEIGHT, WIDTH).astype(np.float64)
    grid[:JUNK_ROWS] = 0
    cols, rows = SHIFT[var]
    grid = np.roll(np.roll(grid, cols, axis=1), rows, axis=0)
    grid[rows:] = 0                              # the rolled-over southern row lands in the north
    grid[~np.isfinite(grid) | (np.abs(grid) > MAX_SPEED)] = 0
    return grid


def symmetric(largest):
    """A range whose code 128 is exactly zero: -M·128/127 .. M, so still water stays still
    (with the sea's own min and max, zero fell between codes and drifted by ~0.3 cm/s; wwolf, #89)."""
    m = round(largest or 1.0, 4)
    return [-m * 128 / 127, m]


def bake(stamps):
    import numpy as np
    from PIL import Image

    total = {v: np.zeros((HEIGHT, WIDTH)) for v in VARS}
    count = np.zeros((HEIGHT, WIDTH))
    for stamp in stamps:
        u = corrected("UVEL", (RAW / "UVEL" / f"{stamp}.f4be").read_bytes())
        v = corrected("VVEL", (RAW / "VVEL" / f"{stamp}.f4be").read_bytes())
        sea = ~((u == 0) & (v == 0))             # land comes as exact zeros
        total["UVEL"] += np.where(sea, u, 0)
        total["VVEL"] += np.where(sea, v, 0)
        count += sea
    land = count == 0
    with np.errstate(invalid="ignore", divide="ignore"):
        u, v = (np.where(land, 0, total[k] / np.maximum(count, 1)) for k in VARS)
    # south-first, longitude from 0 -> north-first, longitude from -180
    u, v, land = (np.flipud(np.roll(a, WIDTH // 2, axis=1)) for a in (u, v, land))
    rgb = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    scale = {}
    for i, (key, grid) in enumerate((("u", u), ("v", v))):
        lo, hi = symmetric(float(np.abs(grid[~land]).max()))
        rgb[..., i] = np.rint((np.clip(grid, lo, hi) - lo) / (hi - lo) * 255).astype(np.uint8)
        scale[key] = [lo, hi]
    rgb[..., 2] = np.where(land, 0, 255)
    speed = np.hypot(u, v)[~land]
    out = io.BytesIO()
    Image.fromarray(rgb, "RGB").save(out, "PNG", optimize=True)
    return out.getvalue(), scale, {
        "p50": round(float(np.percentile(speed, 50)), 4),
        "p90": round(float(np.percentile(speed, 90)), 4),
        "p99": round(float(np.percentile(speed, 99)), 4),
        "max": round(float(speed.max()), 4),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--from", dest="first", type=int, default=1992)
    parser.add_argument("--to", dest="last", type=int, default=2018)
    parser.add_argument("--pause", type=float, default=1.0)
    parser.add_argument("--bake-only", action="store_true", help="bake from the raw layers already on disk")
    args = parser.parse_args(argv)

    stamps_path = RAW / "stamps.json"
    if args.bake_only:
        stamps = json.loads(stamps_path.read_text())["stamps"]
    else:
        both = listed("UVEL") & listed("VVEL")
        stamps = monthly(sorted(both), args.first, args.last)
        RAW.mkdir(parents=True, exist_ok=True)
        stamps_path.write_text(json.dumps({"from": args.first, "to": args.last, "stamps": stamps}, indent=1))
        for n, stamp in enumerate(stamps, 1):
            for var in VARS:
                path = RAW / var / f"{stamp}.f4be"
                if path.exists() and path.stat().st_size == WIDTH * HEIGHT * 4:
                    continue
                for attempt in range(3):
                    try:
                        fetch_surface(var, stamp)
                        break
                    except Exception as exc:  # noqa: BLE001 — retry any transport error
                        print(f"{var} {stamp}: {exc} (try {attempt + 1})", file=sys.stderr)
                        time.sleep(5 * (attempt + 1))
                else:
                    raise SystemExit(f"{var} {stamp}: giving up")
                time.sleep(args.pause)
            print(f"{n}/{len(stamps)} {stamp}", flush=True)

    png, scale, speed = bake(stamps)
    meta = {
        "width": WIDTH, "height": HEIGHT, "depth_m": 5, "days": 3,
        "period": [stamps[0][:4], stamps[-1][:4]], "samples": len(stamps),
        "u": scale["u"], "v": scale["v"], "speed": speed, "url": BASE, "citation": CITATION,
    }
    present_catalogue.write_section("ocean", {"mean": (png, "png")}, meta)
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main()
