#!/usr/bin/env python3
"""Measure whether a location pin can ride its plate through the viewer's timeline.

A pin is a present-day place given a plate number by the packed continent polygons and
carried to any age by that plate's rotation. Nothing here changes the viewer; the script
reads the packed plate models and the derived fields and prints the tables that
devlog wwolf P01 asks for:

  Q2  how much of the globe and of today's land the polygons give a plate to, and how
      far back each reference place can be carried;
  Q1  whether a carried place stays on the land drawn by each surface, against the same
      place left where it is today;
  Q3  how far an exactly rotated pin sits from the surface between two stops, where the
      surface is moved by the gap's Gaussian travel field instead;
  Q4  how far the models put the same place from the PALEOMAP position;
  Q6  how far apart two pins are under each model, and how much the models disagree.

Offline. Run with .venv/bin/python scripts/assess_pin.py
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from measure_longitude_offsets import MAP_AGES, PackedModel  # noqa: E402
from rotation_model import rotate  # noqa: E402

MODELS = ["paleomap2016", "merdith2021", "muller2022", "cao2024", "matthews2016",
          "torsvikcocks2017"]
SURFACE_MODEL = "paleomap2016"   # the edition the default surface and the PaleoDEMs share
EARTH_RADIUS_KM = 6371.0
NEAR_COAST_DEG = 2.0             # a coast may move this far under a place; further is a miss
SHELF_M = -1000.0                # above this a PaleoDEM cell is continent, flooded or not
MAX_MOTIONS = 16                 # the shader's control points (core/globe.py)
SPREAD_AGES = [100, 200, 300, 400, 500]

# Present-day places, longitude then latitude. Interiors are stable continental crust; the
# hard ones are young, accreted or deforming crust, where a rigid polygon is a poor fit.
INTERIORS = {
    "Winnipeg": (-97.14, 49.90), "Chicago": (-87.63, 41.88), "Dallas": (-96.80, 32.78),
    "Yellowknife": (-114.37, 62.45), "Greenland Summit": (-38.46, 72.58),
    "Brasilia": (-47.88, -15.79), "Manaus": (-60.02, -3.12), "Buenos Aires": (-58.38, -34.60),
    "Johannesburg": (28.05, -26.20), "Kinshasa": (15.31, -4.33), "Timbuktu": (-3.00, 16.77),
    "Cairo": (31.24, 30.04), "Nairobi": (36.82, -1.29),
    "Stockholm": (18.07, 59.33), "Moscow": (37.62, 55.76), "Paris": (2.35, 48.86),
    "Yakutsk": (129.73, 62.03), "Novosibirsk": (82.93, 55.03), "Astana": (71.43, 51.13),
    "Beijing": (116.40, 39.90), "Seoul": (126.98, 37.57), "Chengdu": (104.07, 30.57),
    "Nagpur": (79.09, 21.15), "Riyadh": (46.72, 24.69),
    "Alice Springs": (133.88, -23.70), "Perth": (115.86, -31.95),
    "Vostok": (106.80, -78.46), "Dome C": (123.30, -75.10),
}
HARD = {
    "Reykjavik": (-21.94, 64.15), "Tokyo": (139.69, 35.69), "Auckland": (174.76, -36.85),
    "Antarctic Peninsula": (-64.26, -65.25), "Lhasa": (91.10, 29.65),
    "Los Angeles": (-118.24, 34.05), "Rome": (12.50, 41.90), "Jakarta": (106.85, -6.21),
}
PLACES = {**INTERIORS, **HARD}
PAIRS = [("Chicago", "Winnipeg"), ("Johannesburg", "Kinshasa"), ("Brasilia", "Kinshasa"),
         ("Chicago", "Paris"), ("Nagpur", "Novosibirsk"), ("Nagpur", "Johannesburg"),
         ("Alice Springs", "Vostok"), ("Stockholm", "Chicago"), ("Moscow", "Yakutsk"),
         ("Beijing", "Chengdu")]


def unit(longitude, latitude):
    lon, lat = np.radians(longitude), np.radians(latitude)
    return np.stack([np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)], axis=-1)


def separation(first, second):
    """Great-circle angle in degrees between two (longitude, latitude) places."""
    a, b = unit(*first), unit(*second)
    return math.degrees(math.atan2(np.linalg.norm(np.cross(a, b)), float(a @ b)))


def inside(points, ring):
    """Which unit vectors lie in a spherical ring, by the turning of its vertices' bearings.

    Seen from a place inside, the bearings to the ring's vertices go once around; from
    outside they come back to where they started. That holds across the antimeridian and
    over a pole, where a longitude/latitude ray test does not. It cannot tell a place from
    its antipode, so the caller keeps to rings narrower than a hemisphere.
    """
    z = points[:, 2]
    flat = np.maximum(np.hypot(points[:, 0], points[:, 1]), 1e-12)
    east = np.stack([-points[:, 1] / flat, points[:, 0] / flat, np.zeros_like(z)], axis=1)
    north = np.cross(points, east)
    bearing = np.arctan2(ring @ east.T, ring @ north.T)          # vertices x points
    step = np.diff(bearing, axis=0)
    step = (step + np.pi) % (2 * np.pi) - np.pi
    return np.abs(step.sum(axis=0)) > np.pi


class Shapes:
    """A model's present-day continent polygons, ready to answer which plate a place is on."""

    def __init__(self, model):
        self.features = []
        self.wide = 0
        for feature in model.shapes:
            rings = []
            for flat in feature["rings"]:
                ring = unit(np.array(flat[0::2]), np.array(flat[1::2]))
                rings.append(np.vstack([ring, ring[:1]]))
            if not rings:
                continue
            every = np.vstack(rings)
            centre = every.mean(axis=0)
            centre /= np.linalg.norm(centre) or 1.0
            reach = float(np.min(every @ centre))                  # cosine of the cap's radius
            if reach <= 0.0:
                self.wide += 1                                      # wider than a hemisphere
                continue
            self.features.append((feature["pid"], feature["from"], feature["to"], centre, reach, rings))

    def plates(self, points, age=0.0, turns=None):
        """For each unit vector, the (plate, from) of every polygon holding it at `age`.

        `points` are at their `age` positions; `turns` gives each plate's rotation at that
        age, used to take them back to the present-day polygons.
        """
        found = [[] for _ in points]
        for pid, begin, end, centre, reach, rings in self.features:
            if age > begin + 1e-9 or age < end - 1e-9:
                continue
            here = points
            if turns is not None:
                turn = turns(pid)
                if turn is None:
                    continue
                here = points @ turn                               # inverse of a rotation matrix
            near = np.nonzero(here @ centre >= reach - 1e-9)[0]
            if not len(near):
                continue
            held = np.zeros(len(near), dtype=bool)
            for ring in rings:                                     # even-odd, so holes are holes
                held ^= inside(here[near], ring)
            for index in near[held]:
                found[index].append((pid, begin))
        return found


def matrix(quaternion):
    w, x, y, z = quaternion
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                     [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                     [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])


def choose(found):
    """One plate for a pin: the polygon that goes furthest back, and whether plates disagree."""
    if not found:
        return None, None, False
    pid, begin = max(found, key=lambda item: item[1])
    return pid, begin, len({item[0] for item in found}) > 1


def carried(model, pid, place, age):
    turn = model.rotation(pid, age)
    return None if turn is None else rotate(turn, place[0], place[1])


class Field:
    """A derived field's signed distance to the coast, in degrees, land positive."""

    def __init__(self, path):
        image = Image.open(path)
        data = np.asarray(image)
        self.red = data if data.ndim == 2 else data[..., 0]
        # build_paleodem.texture: twelve bits of height over -9000..6000 m in green and blue.
        self.height12 = None if data.ndim == 2 else data[..., 1].astype(int) * 16 + data[..., 2]
        self.height, self.width = self.red.shape
        # segment_landmass.FIELD_SCALE: two grey levels per pixel, zero at 128.
        self.degrees_per_level = 0.5 * 360.0 / self.width

    def cell(self, place):
        column = int((place[0] + 180.0) / 360.0 * self.width) % self.width
        row = min(self.height - 1, max(0, int((90.0 - place[1]) / 180.0 * self.height)))
        return row, column

    def at(self, place):
        return (float(self.red[self.cell(place)]) - 128.0) * self.degrees_per_level

    def metres(self, place):
        return -9000.0 + float(self.height12[self.cell(place)]) / 4095.0 * 15000.0


def catalogue(path, directory, name):
    maps = json.loads((ROOT / path).read_text())["maps"]
    return [(float(item["age_ma"]), ROOT / directory / name(item)) for item in maps]


def surfaces():
    return {
        "paleoatlas2016": catalogue("sources/paleomap-atlas-2016.json", "data/derived/paleoatlas",
                                    lambda item: f"{item['id']}-field.png"),
        "paleodem": catalogue("sources/paleodem-slices.json", "data/derived/paleodem",
                              lambda item: f"{item['id']}-field.png"),
        "scotese2002": [(age, ROOT / "data/derived/segmentation" / f"{stem}-field.png")
                        for stem, age in MAP_AGES if stem != "LGM"],
    }


def table(header, rows):
    print("| " + " | ".join(header) + " |")
    print("|" + "---|" * len(header))
    for row in rows:
        print("| " + " | ".join(str(cell) for cell in row) + " |")
    print()


def assign(models, shapes):
    """Each place's plate under each model: {model: {place: (pid, from, contested)}}."""
    names = list(PLACES)
    points = unit(np.array([PLACES[name][0] for name in names]),
                  np.array([PLACES[name][1] for name in names]))
    return {key: dict(zip(names, (choose(found) for found in shapes[key].plates(points))))
            for key in models}


def reach(model, pid, begin, deepest):
    """The oldest whole 5 Myr step a pin can be carried to: its land exists and has a pole."""
    oldest = 0
    for age in range(0, int(deepest) + 1, 5):
        if age > begin + 1e-9 or model.rotation(pid, float(age)) is None:
            break
        oldest = age
    return oldest


def coverage(models, shapes, plates_of):
    print("## Q2. Plate numbers: cover, contested ground, reach\n")
    lons, lats = np.meshgrid(np.arange(-179.0, 180.0, 2.0), np.arange(-89.0, 90.0, 2.0))
    lons, lats = lons.ravel(), lats.ravel()
    points = unit(lons, lats)
    area = np.cos(np.radians(lats))
    today = Field(ROOT / "data/derived/paleoatlas/paleoatlas-000-field.png")
    land = np.array([today.at(place) >= 0.0 for place in zip(lons, lats)])
    everywhere = np.ones(len(lats), dtype=bool)

    def share(mask, within):
        return f"{100 * area[mask & within].sum() / area[within].sum():.1f}"

    rows = []
    for key in models:
        found = shapes[key].plates(points)
        count = np.array([len({pid for pid, _ in item}) for item in found])
        rows.append([key, len(shapes[key].features), shapes[key].wide, share(count == 1, everywhere),
                     share(count > 1, everywhere), share(count >= 1, land), share(count > 1, land)])
    table(["model", "polygons", "wider than a hemisphere (skipped)", "globe with one plate %",
           "globe contested %", "today's land with a plate %", "today's land contested %"], rows)

    rows = []
    for name in PLACES:
        row = [name + (" (hard)" if name in HARD else "")]
        for key in models:
            pid, begin, contested = plates_of[key][name]
            if pid is None:
                row.append("none")
                continue
            oldest = reach(models[key], pid, begin, models[key].deepest)
            row.append(f"{pid}{'*' if contested else ''} → {oldest}")
        rows.append(row)
    print("Plate number and the oldest age (Ma, 5 Myr steps) each place can be carried to."
          " `*` marks a place inside polygons of more than one plate.\n")
    table(["place"] + list(models), rows)


def past_pin_check(model, shapes, plates_of):
    """A pin dropped at a past age must find the plate its present-day place was given."""
    def turns(plate):
        turn = model.rotation(plate, 200.0)
        return None if turn is None else matrix(turn)

    checked = 0
    for name in INTERIORS:
        pid, begin, _ = plates_of[name]
        if pid is None or begin < 200.0:
            continue
        there = carried(model, pid, PLACES[name], 200.0)
        if there is None:
            continue
        found = shapes.plates(unit(np.array([there[0]]), np.array([there[1]])), 200.0, turns)[0]
        assert pid in {plate for plate, _ in found}, (name, pid, found)
        checked += 1
    print(f"Self-check: {checked} interiors dropped at 200 Ma find the plate they were given today.\n")


def on_land(model, plates_of):
    print("## Q1. Does a carried place stay on its land?\n")
    print(f"Share of (place, map) pairs on land or within {NEAR_COAST_DEG:g}° of a coast, for the"
          f" {len(INTERIORS)} interiors carried by `{SURFACE_MODEL}`, against the same places left"
          " at today's coordinates. Only maps the place's polygon reaches. A craton under a"
          " shallow sea is off the land but not off its continent, so where the surface has"
          f" heights the share above {SHELF_M:g} m is given too, and the verdict uses it.\n")
    bins = [(0, 100), (100, 200), (200, 300), (300, 400), (400, 541)]
    verdicts = {}
    for surface, maps in surfaces().items():
        # Per age bin: carried and left in place near land, the same on the continent, pairs.
        tally = {span: [0, 0, 0, 0, 0] for span in bins}
        misses = {}
        heights = False
        for age, path in maps:
            if not path.exists():
                continue
            span = next((item for item in bins if item[0] <= age < item[1]), None)
            if span is None:
                continue
            field = Field(path)
            heights = field.height12 is not None
            for name in INTERIORS:
                pid, begin, _ = plates_of[name]
                if pid is None or age > begin + 1e-9:
                    continue
                there = carried(model, pid, PLACES[name], age)
                if there is None:
                    continue
                near = field.at(there) >= -NEAR_COAST_DEG
                tally[span][0] += near
                tally[span][1] += field.at(PLACES[name]) >= -NEAR_COAST_DEG
                if heights:
                    near = field.metres(there) >= SHELF_M
                    tally[span][2] += near
                    tally[span][3] += field.metres(PLACES[name]) >= SHELF_M
                tally[span][4] += 1
                if not near:
                    misses.setdefault(name, []).append(age)
            if age == 0.0:
                on = sum(field.at(PLACES[name]) >= 0.0 for name in INTERIORS)
                # The grid is read the right way up. Not all of them: the 2002 segmentation
                # does not take the ice of Greenland and Antarctica for land.
                assert on >= 0.75 * len(INTERIORS), (surface, on)
        rows = []
        spans = [(f"{span[0]}–{min(span[1], 540)} Ma", counts) for span, counts in tally.items()]
        spans.append(("all", [sum(item[index] for item in tally.values()) for index in range(5)]))
        for label, counts in spans:
            if counts[4]:
                shown = counts[:4] if heights else counts[:2]
                rows.append([label, counts[4]] + [f"{100 * count / counts[4]:.0f}" for count in shown])
        total = spans[-1][1]
        verdicts[surface] = total[2 if heights else 0] / total[4]
        print(f"### {surface}\n")
        table(["ages", "pairs", "carried near land %", "left in place near land %"]
              + (["carried on continent %", "left in place on continent %"] if heights else []), rows)
        worst = sorted(misses.items(), key=lambda item: -len(item[1]))[:8]
        print("Most misses (" + ("continent" if heights else "land") + " test): "
              + "; ".join(f"{name} {len(ages)} ({min(ages):g}–{max(ages):g} Ma)" for name, ages in worst)
              + "\n")
    return verdicts


def travel(place, gap):
    """globe.js travelAt(): the gap's Gaussian-weighted translation at a place, in degrees."""
    east = north = weight = 0.0
    for pair in gap[:MAX_MOTIONS]:
        eastward = ((place[0] - pair["lon"] + 540.0) % 360.0) - 180.0
        northward = place[1] - pair["lat"]
        shrink = math.cos(math.radians(0.5 * (place[1] + pair["lat"])))
        span = math.hypot(eastward * shrink, northward)
        radius = max(pair["radius"], 1.0)
        pull = math.exp(-0.5 * span * span / (radius * radius))
        east += pull * (((pair["to_lon"] - pair["lon"] + 540.0) % 360.0) - 180.0)
        north += pull * (pair["to_lat"] - pair["lat"])
        weight += pull
    if weight <= 0.0:
        return 0.0, 0.0
    t = max(0.0, min(1.0, (weight - 0.05) / 0.4))
    ease = t * t * (3.0 - 2.0 * t)
    return east / weight * ease, north / weight * ease


def drawn_at(origin, gap, share):
    """Where the shader draws ground that a frame holds at `origin`: x with x - share*travel(x) = origin."""
    place = origin
    for _ in range(8):
        east, north = travel(place, gap)
        place = (origin[0] + share * east, max(-90.0, min(90.0, origin[1] + share * north)))
    return place


def between_stops(model, plates_of):
    print("## Q3. Between two stops: exact pin against the moved surface\n")
    print("Half way across each gap the surface shows the older map pushed forward and the newer"
          " pulled back by the travel field; the pin is at its exact rotation. The distance is"
          " the larger of the two, in degrees, over every interior the gap's ages reach.\n")
    rows = []
    for series, directory, source in [("paleoatlas2016", "paleoatlas", "sources/paleomap-atlas-2016.json"),
                                      ("paleodem", "paleodem", "sources/paleodem-slices.json")]:
        ages = {item["id"]: float(item["age_ma"])
                for path in ("sources/paleomap-atlas-2016.json", source)
                for item in json.loads((ROOT / path).read_text())["maps"]}
        gaps = json.loads((ROOT / "data/derived" / directory / "motions.json").read_text())["gaps"]
        drifts, young, worst = [], [], (0.0, None)
        for gap in gaps:
            older, newer = ages.get(gap["from"]), ages.get(gap["to"])
            if older is None or newer is None or older > 540.0:
                continue
            for name in INTERIORS:
                pid, begin, _ = plates_of[name]
                if pid is None or older > begin + 1e-9:
                    continue
                ends = [carried(model, pid, PLACES[name], age) for age in (older, 0.5 * (older + newer), newer)]
                if None in ends:
                    continue
                drift = max(separation(ends[1], drawn_at(ends[0], gap["pairs"], 0.5)),
                            separation(ends[1], drawn_at(ends[2], gap["pairs"], -0.5)))
                drifts.append(drift)
                young.append(older <= 300.0)
                if drift > worst[0]:
                    worst = (drift, f"{name}, {older:g}→{newer:g} Ma")
        drifts, young = np.array(drifts), np.array(young)
        rows.append([series, len(gaps), len(drifts), f"{np.median(drifts):.2f}",
                     f"{np.percentile(drifts, 95):.2f}", f"{drifts.max():.2f}", worst[1],
                     f"{100 * (drifts > 1.0).mean():.1f}", f"{100 * (drifts[young] > 1.0).mean():.1f}",
                     f"{100 * (drifts[~young] > 1.0).mean():.1f}", f"{100 * (drifts > 2.0).mean():.1f}"])
    table(["series", "gaps", "pairs", "median °", "95th °", "max °", "worst", "over 1° %",
           "over 1°, to 300 Ma %", "over 1°, older %", "over 2° %"], rows)


def model_spread(models, plates_of):
    print("## Q4. The same place under each model\n")
    print(f"Median (and largest) distance in degrees from the `{SURFACE_MODEL}` position, over the"
          " interiors both models can carry to that age; the count in brackets.\n")
    rows = []
    for age in SPREAD_AGES:
        row = [f"{age} Ma"]
        for key in models:
            if key == SURFACE_MODEL:
                continue
            apart = []
            for name in INTERIORS:
                places = []
                for each in (SURFACE_MODEL, key):
                    pid, begin, _ = plates_of[each][name]
                    ok = pid is not None and age <= begin + 1e-9
                    places.append(carried(models[each], pid, PLACES[name], float(age)) if ok else None)
                if None not in places:
                    apart.append(separation(*places))
            row.append(f"{np.median(apart):.1f} ({max(apart):.1f}) [{len(apart)}]" if apart else "–")
        rows.append(row)
    table(["age"] + [key for key in models if key != SURFACE_MODEL], rows)


def pair_distances(models, plates_of):
    print("## Q6. Distance between two pins\n")
    print("Kilometres along the great circle. Each cell is the smallest and largest distance any"
          " model gives, with the number of models that reach that age for both places.\n")
    rows, rigid = [], 0
    for first, second in PAIRS:
        now = math.radians(separation(PLACES[first], PLACES[second])) * EARTH_RADIUS_KM
        row = [f"{first} – {second}", f"{now:.0f}"]
        for age in SPREAD_AGES:
            found = []
            for key, model in models.items():
                ends = []
                for name in (first, second):
                    pid, begin, _ = plates_of[key][name]
                    ok = pid is not None and age <= begin + 1e-9
                    ends.append(carried(model, pid, PLACES[name], float(age)) if ok else None)
                if None in ends:
                    continue
                distance = math.radians(separation(*ends)) * EARTH_RADIUS_KM
                found.append(distance)
                if plates_of[key][first][0] == plates_of[key][second][0]:
                    assert abs(distance - now) < 0.5, (key, first, second, age, distance, now)
                    rigid += 1
            row.append(f"{min(found):.0f}–{max(found):.0f} [{len(found)}]" if found else "–")
        rows.append(row)
    table(["pair", "today"] + [f"{age} Ma" for age in SPREAD_AGES], rows)
    print(f"Self-check: {rigid} same-plate distances stayed within 0.5 km of today's.\n")


def main():
    models = {key: PackedModel(key) for key in MODELS}
    for key, model in models.items():
        manifest = json.loads((ROOT / "sources/plate-models" / f"{key}.json").read_text())
        model.deepest = float(max(manifest["covers_ma"]))
    shapes = {key: Shapes(model) for key, model in models.items()}
    plates_of = assign(models, shapes)

    print("# Location pin: measurements for wwolf P01\n")
    coverage(models, shapes, plates_of)
    past_pin_check(models[SURFACE_MODEL], shapes[SURFACE_MODEL], plates_of[SURFACE_MODEL])
    verdicts = on_land(models[SURFACE_MODEL], plates_of[SURFACE_MODEL])
    between_stops(models[SURFACE_MODEL], plates_of[SURFACE_MODEL])
    model_spread(models, plates_of)
    pair_distances(models, plates_of)
    print("## Verdict on Q1\n")
    for surface, share in verdicts.items():
        print(f"- {surface}: {100 * share:.1f} % of carried pairs kept their ground"
              f" ({'pass' if share >= 0.9 else 'fail'} at 90 %)")


if __name__ == "__main__":
    main()
