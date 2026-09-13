#!/usr/bin/env python3
"""Measure how far plate models sit from each other and from the Scotese maps.

Backs the numbers in docs/palaeolongitude.md. Three measurements:

1. For each map age, the rotation about the spin axis that best overlaps a model's land
   with the land segmented from the Scotese map. A rotation about the spin axis is the
   freedom palaeomagnetism leaves open, and in an equirectangular raster it is a
   horizontal roll, so the search is a roll over whole degrees.
2. Where the same point on a craton lands in two models, split into longitude and
   latitude. A pure spin-axis disagreement moves longitude only.
3. Torsvik & Cocks read against plate 0, which includes the true polar wander layer
   its rotation file places between plate 1 and plate 0, and against plate 1, which
   does not.

Needs the packed plate models (scripts/pack_plates.py) and the segmentation fields
(scripts/segment_landmass.py), both gitignored.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rotation_model import (IDENTITY, _quaternion, conjugate, multiply,  # noqa: E402
                            rotate, slerp)

ROOT = Path(__file__).resolve().parents[1]
PLATES = ROOT / "data/derived/plates"
FIELDS = ROOT / "data/derived/segmentation"
WIDTH, HEIGHT = 360, 180

# Map stems and the ages they are catalogued at.
MAP_AGES = [("000", 0.0), ("LGM", 0.018), ("014", 14.0), ("050", 50.2), ("066", 66.0),
            ("094", 94.0), ("152", 152.0), ("195", 195.0), ("237", 237.0), ("255", 255.0),
            ("306", 306.0), ("342", 356.0), ("390", 390.0), ("425", 425.0),
            ("458", 458.0), ("514", 514.0), ("650", 650.0)]

POINTS = [(701, "Africa", 20.0, 5.0), (201, "South America", -58.0, -13.0),
          (101, "North America", -100.0, 45.0), (302, "Baltica", 25.0, 60.0)]


class PackedModel:
    """A packed rotation model, composed as scripts/rotation_model.py does."""

    def __init__(self, model):
        document = json.loads((PLATES / model / "rotations.json").read_text())
        self.sequences = {}
        self.spans = {}
        for key, flat in document["sequences"].items():
            moving, fixed = (int(part) for part in key.split(":"))
            samples = [flat[index:index + 4] for index in range(0, len(flat), 4)]
            self.sequences[(moving, fixed)] = samples
            self.spans.setdefault(moving, []).append((fixed, samples[0][0], samples[-1][0]))
        # The narrower, later-starting sequence wins where two overlap.
        for spans in self.spans.values():
            spans.sort(key=lambda span: span[1], reverse=True)
        self.shapes = json.loads((PLATES / model / "continents.json").read_text())["features"]

    def _relative(self, samples, time):
        if time < samples[0][0] - 1e-9 or time > samples[-1][0] + 1e-9:
            return None
        previous = samples[0]
        for sample in samples:
            if sample[0] >= time - 1e-9:
                if abs(sample[0] - previous[0]) < 1e-9 or abs(sample[0] - time) < 1e-9:
                    return _quaternion(*sample[1:])
                fraction = (time - previous[0]) / (sample[0] - previous[0])
                start, end = _quaternion(*previous[1:]), _quaternion(*sample[1:])
                return multiply(start, slerp(IDENTITY, multiply(conjugate(start), end), fraction))
            previous = sample
        return _quaternion(*samples[-1][1:])

    def _to_root(self, plate, time, seen=()):
        if plate == 0:
            return IDENTITY
        if plate in seen:
            return None
        for fixed, start, end in self.spans.get(plate, []):
            if not start - 1e-9 <= time <= end + 1e-9:
                continue
            relative = self._relative(self.sequences[(plate, fixed)], time)
            if relative is None:
                continue
            upstream = self._to_root(fixed, time, seen + (plate,))
            if upstream is not None:
                return multiply(upstream, relative)
        return None

    def rotation(self, plate, time, anchor=0):
        """Rotation of `plate` at `time`, expressed relative to plate `anchor`."""
        total = self._to_root(plate, time)
        if total is None or anchor == 0:
            return total
        frame = self._to_root(anchor, time)
        return None if frame is None else multiply(conjugate(frame), total)


def rasterise(model, age, anchor=0):
    canvas = Image.new("L", (3 * WIDTH, HEIGHT), 0)
    draw = ImageDraw.Draw(canvas)
    for feature in model.shapes:
        if not feature["to"] - 1e-9 <= age <= feature["from"] + 1e-9:
            continue
        turn = model.rotation(feature["pid"], age, anchor)
        if turn is None:
            continue
        for ring in feature["rings"]:
            points, last = [], None
            for index in range(0, len(ring), 2):
                longitude, latitude = rotate(turn, ring[index], ring[index + 1])
                if last is not None:
                    # Unwrap, so a ring crossing the antimeridian is drawn whole.
                    while longitude - last > 180:
                        longitude -= 360
                    while longitude - last < -180:
                        longitude += 360
                last = longitude
                points.append((longitude, latitude))
            if len(points) < 3:
                continue
            for shift in (-360, 0, 360):
                draw.polygon([((x + 180 + shift) / 360 * WIDTH + WIDTH, (90 - y) / 180 * HEIGHT)
                              for x, y in points], fill=255)
    return np.asarray(canvas)[:, WIDTH:2 * WIDTH] > 0


def scotese_land(stem):
    field = Image.open(FIELDS / f"{stem}-field.png").resize((WIDTH, HEIGHT), Image.BILINEAR)
    return np.asarray(field).astype(float) > 128


# Equirectangular cells shrink toward the poles, so overlap is weighted by area.
WEIGHTS = np.cos(np.radians(90 - (np.arange(HEIGHT) + 0.5) / HEIGHT * 180))[:, None] \
    * np.ones((1, WIDTH))


def overlap(first, second):
    union = (WEIGHTS * (first | second)).sum()
    return (WEIGHTS * (first & second)).sum() / union if union else 0.0


def best_roll(land, target):
    scores = [overlap(np.roll(land, shift, axis=1), target) for shift in range(-180, 180)]
    return scores[180], int(np.argmax(scores)) - 180, max(scores)


def reach(model_id):
    manifest = json.loads((ROOT / f"sources/plate-models/{model_id}.json").read_text())
    return manifest["covers_ma"][1]


def against_scotese(models):
    for model_id in models:
        model = PackedModel(model_id)
        print(f"\n{model_id}: rotation about the spin axis that best matches the Scotese land")
        print(f"  {'map':>4} {'age':>7} {'overlap at 0':>13} {'best shift':>11} {'overlap':>8}")
        for stem, age in MAP_AGES:
            if age > reach(model_id):
                continue
            at_zero, shift, best = best_roll(rasterise(model, age), scotese_land(stem))
            print(f"  {stem:>4} {age:7.1f} {at_zero:13.3f} {shift:+10d}° {best:8.3f}")


def points_between(first_id, second_id, ages):
    first, second = PackedModel(first_id), PackedModel(second_id)
    print(f"\nSame point in both models, {first_id} minus {second_id}")
    print(f"  {'age':>5} {'plate':14} {'longitude':>10} {'latitude':>9}")
    for age in ages:
        for plate, name, longitude, latitude in POINTS:
            a, b = first.rotation(plate, age), second.rotation(plate, age)
            if a is None or b is None:
                continue
            pa, pb = rotate(a, longitude, latitude), rotate(b, longitude, latitude)
            delta = (pa[0] - pb[0] + 540) % 360 - 180
            print(f"  {age:5.0f} {name:14} {delta:+9.1f}° {pa[1] - pb[1]:+8.1f}°")


def torsvik_layers(ages):
    torsvik, merdith = PackedModel("torsvikcocks2017"), PackedModel("merdith2021")
    print("\nTorsvik & Cocks latitude minus Merdith, against plate 0 (with TPW) and plate 1")
    print(f"  {'age':>5} {'plate':14} {'plate 0':>8} {'plate 1':>8}")
    for age in ages:
        for plate, name, longitude, latitude in POINTS:
            reference = merdith.rotation(plate, age)
            if reference is None:
                continue
            base = rotate(reference, longitude, latitude)[1]
            row = []
            for anchor in (0, 1):
                turn = torsvik.rotation(plate, age, anchor)
                row.append(float("nan") if turn is None
                           else rotate(turn, longitude, latitude)[1] - base)
            print(f"  {age:5.0f} {name:14} {row[0]:+7.1f}° {row[1]:+7.1f}°")
    print("\nTorsvik & Cocks against the Scotese land, plate 0 and plate 1")
    print(f"  {'age':>5} {'plate 0 shift':>14} {'overlap':>8} {'plate 1 shift':>14} {'overlap':>8}")
    for stem, age in MAP_AGES:
        if age > reach("torsvikcocks2017"):
            continue
        target = scotese_land(stem)
        cells = [best_roll(rasterise(torsvik, age, anchor), target)[1:] for anchor in (0, 1)]
        print(f"  {age:5.0f} {cells[0][0]:+13d}° {cells[0][1]:8.3f} "
              f"{cells[1][0]:+13d}° {cells[1][1]:8.3f}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("section", nargs="?", default="all",
                        choices=("all", "scotese", "points", "layers"))
    args = parser.parse_args()
    ages = [100.0, 200.0, 255.0, 306.0, 356.0, 425.0, 514.0]
    if args.section in ("all", "scotese"):
        against_scotese(["torsvikcocks2017", "merdith2021"])
    if args.section in ("all", "points"):
        points_between("torsvikcocks2017", "merdith2021", ages)
    if args.section in ("all", "layers"):
        torsvik_layers([306.0, 356.0, 425.0, 514.0])


if __name__ == "__main__":
    main()
