#!/usr/bin/env python3
"""Turn the EarthByte plate model into two files the viewer can load.

GPML is XML: each feature carries a geometry, the plate it rides on, and the span of
time it exists for. The rotation file is a plain-text list of total reconstruction
poles. Neither shape suits a browser, so both are repacked as compact JSON, with the
coastlines simplified because a 100,000-point outline is far finer than a globe a few
hundred pixels across can show.
"""
import argparse
import gzip
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/sources/earthbyte/v1.2.4"
ROTATIONS = SOURCE / "1000_0_rotfile_Merdith_et_al.rot"
# Continents cover the whole billion years and draw one outline per block; coastlines
# are finer but the authors say they are mainly meaningful for the past 400 Ma. The
# viewer shows continents, which is the layer that spans our range.
LAYERS = {
    "continents": SOURCE / "shapes_continents.gpml",
    "coastlines": SOURCE / "shapes_coastlines_Merdith_et_al_v2.gpmlz",
}
OUT = ROOT / "data/derived/plates"

DISTANT_PAST = 1e9
DISTANT_FUTURE = -1e9


def read_text(path):
    if path.suffix == ".gpmlz":
        return gzip.open(path, "rb").read().decode("utf-8", "replace")
    return path.read_text(errors="replace")


def parse_time(value):
    if "distantPast" in value:
        return DISTANT_PAST
    if "distantFuture" in value:
        return DISTANT_FUTURE
    try:
        return float(value)
    except ValueError:
        return DISTANT_PAST


def simplify(points, tolerance):
    """Douglas-Peucker on longitude/latitude, which is enough at this display scale."""
    if len(points) < 3:
        return points
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        first, last = stack.pop()
        if last <= first + 1:
            continue
        ax, ay = points[first]
        bx, by = points[last]
        dx, dy = bx - ax, by - ay
        length = math.hypot(dx, dy)
        worst, index = -1.0, first
        for position in range(first + 1, last):
            px, py = points[position]
            if length < 1e-12:
                distance = math.hypot(px - ax, py - ay)
            else:
                distance = abs(dy * px - dx * py + bx * ay - by * ax) / length
            if distance > worst:
                worst, index = distance, position
        if worst > tolerance:
            keep[index] = True
            stack.extend([(first, index), (index, last)])
    return [point for point, wanted in zip(points, keep) if wanted]


def features(text, tolerance, minimum_points):
    for block in re.findall(r"<gml:featureMember>.*?</gml:featureMember>", text, re.S):
        plate = re.search(r"<gpml:reconstructionPlateId>.*?<gpml:value>(\d+)</gpml:value>",
                          block, re.S)
        if plate is None:
            continue
        begin = re.search(r"<gml:begin>.*?timePosition[^>]*>([^<]+)<", block, re.S)
        end = re.search(r"<gml:end>.*?timePosition[^>]*>([^<]+)<", block, re.S)
        name = re.search(r"<gml:name>([^<]*)</gml:name>", block)
        rings = []
        for raw in re.findall(r"<gml:posList[^>]*>(.*?)</gml:posList>", block, re.S):
            numbers = raw.split()
            # GPML stores latitude first; everything downstream wants longitude first.
            points = [(float(numbers[index + 1]), float(numbers[index]))
                      for index in range(0, len(numbers) - 1, 2)]
            points = simplify(points, tolerance)
            if len(points) >= minimum_points:
                rings.append([round(value, 3) for point in points for value in point])
        if rings:
            yield {"pid": int(plate.group(1)),
                   "from": round(parse_time(begin.group(1)) if begin else DISTANT_PAST, 2),
                   "to": round(parse_time(end.group(1)) if end else DISTANT_FUTURE, 2),
                   "name": (name.group(1) if name else "") or None,
                   "rings": rings}


def rotations(text):
    """Sequences keyed by "moving:fixed", each a flat list of time, lat, lon, angle."""
    sequences = {}
    for line in text.splitlines():
        body = line.split("!", 1)[0].split()
        if len(body) < 6:
            continue
        try:
            moving, fixed = int(body[0]), int(body[5])
            values = [float(value) for value in body[1:5]]
        except ValueError:
            continue
        if any(math.isnan(value) for value in values):
            continue
        sequences.setdefault(f"{moving}:{fixed}", []).append(values)
    for samples in sequences.values():
        samples.sort(key=lambda sample: sample[0])
    return {key: [round(value, 6) for sample in samples for value in sample]
            for key, samples in sequences.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tolerance", type=float, default=0.12,
                        help="simplification tolerance in degrees")
    parser.add_argument("--min-points", type=int, default=4)
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    catalogue = json.loads((ROOT / "sources/earthbyte-merdith2021.json").read_text())
    attribution = {"citation": catalogue["citation"], "license": catalogue["license"]["name"],
                   "license_url": catalogue["license"]["url"],
                   "model": "Merdith et al. 2021", "version": catalogue["archive"]["version"]}

    for layer, path in LAYERS.items():
        shapes = list(features(read_text(path), args.tolerance, args.min_points))
        points = sum(len(ring) // 2 for shape in shapes for ring in shape["rings"])
        document = {"attribution": attribution, "layer": layer,
                    "tolerance_deg": args.tolerance, "features": shapes}
        (OUT / f"{layer}.json").write_text(json.dumps(document, separators=(",", ":")))
        print(f"{layer}: {len(shapes)} features, {points} points")

    model = {"attribution": attribution, "anchor": 0, "sequences": rotations(read_text(ROTATIONS))}
    (OUT / "rotations.json").write_text(json.dumps(model, separators=(",", ":")))

    for name in [f"{layer}.json" for layer in LAYERS] + ["rotations.json"]:
        size = (OUT / name).stat().st_size
        print(f"{name}: {size / 1024:.0f} KiB")
    print(f"simplified at {args.tolerance} deg; "
          f"{len(model['sequences'])} rotation sequences")


if __name__ == "__main__":
    main()
