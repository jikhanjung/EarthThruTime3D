#!/usr/bin/env python3
"""Move the 2016 PaleoAtlas landmasses between maps with the PALEOMAP rotations.

The 2002 masks are carried across a gap by matching named pieces on both maps and
drawing a line between their two centroids. The 2016 masks can do better, because they
are the same edition as a rotation model: each plate-group region found by
scripts/segment_paleoatlas.py is taken back to present-day coordinates with its dominant
plate's rotation at the older map's age, then forward to the newer map's age. The pair of
positions is a real reconstruction of where that region's centre travels, not a guess
from two segmentations.

The result is written to data/derived/paleoatlas/motions.json, one list per gap, oldest
gap first, in the form the viewer's morph already reads (lon, lat, to_lon, to_lat,
radius). The morph still moves each region as a Gaussian-weighted translation of its
centre, so rotation within a region is approximated, not drawn exactly.
"""
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from measure_longitude_offsets import PackedModel  # noqa: E402
from rotation_model import conjugate, rotate  # noqa: E402

CATALOGUE = ROOT / "sources/paleomap-atlas-2016.json"
DERIVED = ROOT / "data/derived/paleoatlas"
OUT = DERIVED / "motions.json"
MODEL = "paleomap2016"

# The same limits the 2002 motions use (core/globe.py): the shader holds 16 control
# points, a region smaller than 4 degrees is an island rather than a continent, and above
# 2 degrees per million years a pair is reported as faster than any measured plate.
MAX_MOTIONS = 16
MIN_RADIUS_DEG = 4.0
FASTEST_DEGREES_PER_MA = 2.0


def separation(first, second):
    lon1, lat1, lon2, lat2 = (math.radians(value) for value in (*first, *second))
    cosine = (math.sin(lat1) * math.sin(lat2)
              + math.cos(lat1) * math.cos(lat2) * math.cos(lon2 - lon1))
    return math.degrees(math.acos(max(-1.0, min(1.0, cosine))))


def carry(model, plate, point, older_age, newer_age):
    """Where `point`, riding `plate` at `older_age`, sits at `newer_age`; None if unknown."""
    before = model.rotation(plate, older_age)
    after = model.rotation(plate, newer_age)
    if before is None or after is None:
        return None
    present = rotate(conjugate(before), point[0], point[1])
    return rotate(after, present[0], present[1])


def gap_pairs(model, older, newer, report):
    span = abs(older["age_ma"] - newer["age_ma"])
    pairs = []
    for piece in report["pieces"]:
        for region in piece.get("regions", []):
            if region["radius_deg"] < MIN_RADIUS_DEG:
                continue
            target = carry(model, region["plate"], region["centroid"],
                           older["age_ma"], newer["age_ma"])
            if target is None:
                continue
            moved = separation(region["centroid"], target)
            rate = moved / span if span else 0.0
            pairs.append({"lon": region["centroid"][0], "lat": region["centroid"][1],
                          "to_lon": round(float(target[0]), 3),
                          "to_lat": round(float(target[1]), 3),
                          "radius": region["radius_deg"], "moved": round(moved, 3),
                          "deg_per_ma": round(rate, 4),
                          "fast": rate > FASTEST_DEGREES_PER_MA,
                          "group": region["group"], "plate": region["plate"]})
    pairs.sort(key=lambda pair: pair["radius"], reverse=True)
    return pairs[:MAX_MOTIONS]


def main():
    maps = json.loads(CATALOGUE.read_text())["maps"]
    model = PackedModel(MODEL)
    reports = {}
    for item in maps:
        path = DERIVED / f"{item['id']}-pieces.json"
        if not path.exists():
            raise SystemExit(f"Missing {path}. Run scripts/segment_paleoatlas.py first.")
        reports[item["id"]] = json.loads(path.read_text())
    gaps = []
    for older, newer in zip(maps, maps[1:]):
        gaps.append({"from": older["id"], "to": newer["id"],
                     "pairs": gap_pairs(model, older, newer, reports[older["id"]])})
    document = {"schema_version": 1, "model": MODEL,
                "catalogue": str(CATALOGUE.relative_to(ROOT)),
                "method": ("Each plate-group region's centroid on the older map is rotated "
                           "back to present-day coordinates with its dominant plate's "
                           "PALEOMAP rotation, then forward to the newer map's age."),
                "gaps": gaps}
    OUT.write_text(json.dumps(document, indent=1))
    counts = [len(gap["pairs"]) for gap in gaps]
    fastest = max((pair["deg_per_ma"] for gap in gaps for pair in gap["pairs"]), default=0.0)
    flagged = sum(pair["fast"] for gap in gaps for pair in gap["pairs"])
    print(f"{OUT.relative_to(ROOT)}: {len(gaps)} gaps, {sum(counts)} pairs "
          f"({min(counts)}-{max(counts)} per gap), fastest {fastest:.2f} deg/Ma, "
          f"{flagged} above {FASTEST_DEGREES_PER_MA}")


if __name__ == "__main__":
    main()
