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
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_plate_model import manifest, member_path, models  # noqa: E402

# Continents cover the whole billion years and draw one outline per block; coastlines
# are finer but the authors say they are mainly meaningful for the past 400 Ma. The
# viewer shows continents, which is the layer that spans our range.
SHAPE_ROLES = ("continents", "coastlines")
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


def dbf_records(path):
    """Attribute rows from a dBASE III table, which is what a shapefile carries.

    Only the fields a plate model needs are wanted, but the format makes it as cheap to
    read them all: a fixed header, then fixed-width rows of text.
    """
    data = path.read_bytes()
    count, header_length, record_length = struct.unpack_from("<IHH", data, 4)
    fields = []
    offset = 32
    while data[offset] != 0x0D:
        name = data[offset:offset + 11].split(b"\0")[0].decode("latin-1")
        length = data[offset + 16]
        fields.append((name, length))
        offset += 32
    rows = []
    for index in range(count):
        start = header_length + index * record_length + 1  # the first byte is a delete flag
        row = {}
        for name, length in fields:
            row[name] = data[start:start + length].decode("latin-1").strip()
            start += length
        rows.append(row)
    return rows


def shapefile_rings(path):
    """Polygon rings from a .shp, as lists of (longitude, latitude).

    One entry per record, each a list of rings, so it lines up with the .dbf rows.
    """
    data = path.read_bytes()
    offset = 100  # the file header
    shapes = []
    while offset < len(data):
        _, content_length = struct.unpack_from(">II", data, offset)
        body = offset + 8
        shape_type = struct.unpack_from("<I", data, body)[0]
        rings = []
        if shape_type == 5:  # polygon
            parts, points = struct.unpack_from("<II", data, body + 36)
            starts = struct.unpack_from(f"<{parts}I", data, body + 44)
            coordinates = struct.unpack_from(f"<{points * 2}d", data, body + 44 + parts * 4)
            for index, first in enumerate(starts):
                last = starts[index + 1] if index + 1 < parts else points
                rings.append([(coordinates[position * 2], coordinates[position * 2 + 1])
                              for position in range(first, last)])
        shapes.append(rings)
        offset = body + content_length * 2
    return shapes


def shapefile_features(path, tolerance, minimum_points):
    """The same shape of record as the GPML reader, from a shapefile pair."""
    rows = dbf_records(path.with_suffix(".dbf"))
    for shape, row in zip(shapefile_rings(path), rows):
        # Plate ids are integers, but dBASE stores numbers as text and some files write
        # them in scientific notation, so read them as numbers rather than digits.
        try:
            plate = int(float(row.get("PLATEID1") or row.get("PLATEID") or ""))
        except ValueError:
            continue
        rings = []
        for points in shape:
            simplified = simplify(points, tolerance)
            if len(simplified) >= minimum_points:
                rings.append([round(value, 3) for point in simplified for value in point])
        if rings:
            # Shapefiles write -999 where GPML says distantPast or distantFuture.
            begin = float(row.get("FROMAGE") or DISTANT_PAST)
            end = float(row.get("TOAGE") or DISTANT_FUTURE)
            yield {"pid": plate,
                   "from": DISTANT_PAST if begin <= -900 else begin,
                   "to": DISTANT_FUTURE if end <= -900 else end,
                   "name": (row.get("NAME") or "").strip() or None,
                   "rings": rings}


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


def rotations(texts):
    """Sequences keyed by "moving:fixed", each a flat list of time, lat, lon, angle.

    A model may split its rotations across files by era, so they merge here. Samples
    that repeat at a join are kept once: the files agree there, and a duplicate time
    would make the interpolation step over a zero-length span.
    """
    sequences = {}
    for line in "\n".join(texts).splitlines():
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
    packed = {}
    for key, samples in sequences.items():
        samples.sort(key=lambda sample: sample[0])
        unique = []
        for sample in samples:
            if unique and abs(unique[-1][0] - sample[0]) < 1e-9:
                continue
            unique.append(sample)
        packed[key] = [round(value, 6) for sample in unique for value in sample]
    return packed


def pack(model, tolerance, minimum_points):
    document = manifest(model)
    roles = {member["role"]: member for member in document["members"]}
    # Several members can share the "rotation" role; the shape roles are one each.
    attribution = {"model": model, "title": document["short_title"],
                   "citation": document["citation"],
                   "license": document["license"]["name"],
                   "license_url": document["license"]["url"],
                   "reference_frame": document["reference_frame"],
                   "covers_ma": document["covers_ma"],
                   "limitations": document["limitations"]}
    directory = OUT / model
    directory.mkdir(parents=True, exist_ok=True)

    written = []
    for role in SHAPE_ROLES:
        if role not in roles:
            continue
        path = member_path(model, roles[role])
        shapes = list(shapefile_features(path, tolerance, minimum_points)
                      if path.suffix == ".shp"
                      else features(read_text(path), tolerance, minimum_points))
        points = sum(len(ring) // 2 for shape in shapes for ring in shape["rings"])
        document_out = {"attribution": attribution, "layer": role,
                        "tolerance_deg": tolerance, "features": shapes}
        (directory / f"{role}.json").write_text(json.dumps(document_out, separators=(",", ":")))
        written.append((f"{role}.json", f"{len(shapes)} features, {points} points"))

    rotation_members = [member for member in document["members"]
                        if member["role"] == "rotation"]
    sequences = rotations([read_text(member_path(model, member))
                           for member in rotation_members])
    (directory / "rotations.json").write_text(json.dumps(
        {"attribution": attribution, "anchor": 0, "sequences": sequences},
        separators=(",", ":")))
    written.append(("rotations.json",
                    f"{len(sequences)} sequences from {len(rotation_members)} file(s)"))

    print(f"{model} ({document['reference_frame']} frame)")
    for name, note in written:
        size = (directory / name).stat().st_size
        print(f"  {name:18} {size / 1024:7.0f} KiB  {note}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("models", nargs="*", default=None,
                        help=f"model ids; default all of {', '.join(models())}")
    parser.add_argument("--tolerance", type=float, default=0.12,
                        help="simplification tolerance in degrees")
    parser.add_argument("--min-points", type=int, default=4)
    args = parser.parse_args()
    for model in (args.models or models()):
        pack(model, args.tolerance, args.min_points)


if __name__ == "__main__":
    main()
