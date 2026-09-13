#!/usr/bin/env python3
"""Turn the pinned sea-level curves into one JSON the viewer reads.

`sealevel-curve.json` holds the long-term Phanerozoic curve of van der Meer et al.
(2022) as [age Ma, mean, min, max, ice] at 1 Myr, oldest first, metres above present
and continental ice in millions of km3 (about 23.5 today), which marks where glacial
sea-level cycles, smoothed over by a 1 Myr curve, existed; the
Late Pleistocene stack of Spratt & Lisiecki (2016) as [age ka, metres] at 1 kyr; and,
for every stop of the elevation timeline, the long-term value at that stop's age. The
viewer draws the first two and uses the third as each slice's own datum, so that an
offset applied between slices is the curve's departure from the slice, never the curve
itself, because each PaleoDEM already carries the sea level of its time.
"""
import json
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "sources/sealevel.json"
SLICES = ROOT / "sources/paleodem-slices.json"
LONG_COLUMNS = (34, 35, 36)      # TGE_SL_isocorr_m AVG, MIN, MAX in Supplementary Table 1
ICE_COLUMN = 22                  # VolLandice_km3 AVG: continental ice, about 23.5e6 today


def long_term(path):
    sheet = openpyxl.load_workbook(path, read_only=True, data_only=True).worksheets[0]
    rows = list(sheet.iter_rows(values_only=True))
    labels = rows[2]
    if labels[LONG_COLUMNS[0]] != "TGE_SL_isocorr_m":
        raise SystemExit(f"Unexpected column layout in {path.name}: {labels[LONG_COLUMNS[0]]}")
    curve = []
    for row in rows[4:]:
        if not isinstance(row[0], (int, float)):
            continue
        age, mean, low, high = row[0], *(row[c] for c in LONG_COLUMNS)
        curve.append([float(age), round(float(mean), 1), round(float(low), 1), round(float(high), 1),
                      round(float(row[ICE_COLUMN]) / 1e6, 1)])
    return sorted(curve, key=lambda point: -point[0])


def pleistocene(path):
    header = None
    points = []
    for line in path.read_text().splitlines():
        if line.startswith("#") or not line.strip():
            continue
        cells = line.split("\t")
        if header is None:
            header = cells
            age, level = header.index("age_calkaBP"), header.index("SeaLev_longPC1")
            continue
        if cells[level] == "NaN":
            continue
        points.append([float(cells[age]), round(float(cells[level]), 1)])
    return points


def interpolate(curve, age):
    for older, newer in zip(curve, curve[1:]):
        if older[0] >= age >= newer[0]:
            span = older[0] - newer[0]
            weight = 0.0 if span == 0 else (older[0] - age) / span
            return round(older[1] + (newer[1] - older[1]) * weight, 1)
    return None


def main():
    manifest = json.loads(MANIFEST.read_text())
    paths = {Path(asset["path"]).name: ROOT / asset["path"] for asset in manifest["assets"]}
    curve = long_term(paths["vandermeer2022-mmc1.xlsx"])
    stack = pleistocene(paths["spratt2016-noaa.txt"])
    stops = {item["id"]: interpolate(curve, float(item["age_ma"]))
             for item in json.loads(SLICES.read_text())["maps"]}
    out = ROOT / "data/derived/paleodem/sealevel-curve.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "source": {"long": manifest["cite"][0], "pleistocene": manifest["cite"][1]},
        "long": curve, "pleistocene": stack, "stops": stops}, separators=(",", ":")) + "\n")
    lows = min(curve, key=lambda p: p[1])
    highs = max(curve, key=lambda p: p[1])
    print(f"long-term: {len(curve)} points, {lows[1]} m at {lows[0]:.0f} Ma to {highs[1]} m at {highs[0]:.0f} Ma")
    print(f"pleistocene: {len(stack)} points, min {min(p[1] for p in stack)} m")
    print(f"{sum(v is not None for v in stops.values())} stops given a datum -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
