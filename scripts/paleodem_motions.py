#!/usr/bin/env python3
"""Move the elevation series' landmasses between grids with the PALEOMAP rotations.

The PaleoDEMs are grids, not pictures, so scripts/segment_paleoatlas.py never ran on
them and they have no pieces of their own. They are the same paleogeography as the 2016
PaleoAtlas, from the same edition: 81 of the 109 grids sit at the age of an atlas map and
the rest are never more than 5 Myr from one. So each gap of the elevation series borrows
the plate-group regions of the atlas map nearest its older end, carries every region's
centroid from that map's age to the gap's older age and on to its newer age with the
region's dominant plate, and writes the pairs in the form the viewer's morph reads. Where
the ages coincide the first step is the identity, and the atlas prelude's gaps come out
the same as the atlas's own.

Written to data/derived/paleodem/motions.json, one list per gap of the series (the three
prelude maps, then the 109 grids), oldest gap first.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from atlas_motions import (FASTEST_DEGREES_PER_MA, MAX_MOTIONS, MIN_RADIUS_DEG, MODEL,  # noqa: E402
                           PackedModel, carry, separation)

ATLAS = ROOT / "sources/paleomap-atlas-2016.json"
GRIDS = ROOT / "sources/paleodem-slices.json"
ATLAS_DERIVED = ROOT / "data/derived/paleoatlas"
OUT = ROOT / "data/derived/paleodem/motions.json"
DEM_OLDEST_MA = 540.0
# The furthest a grid may be from the atlas map it borrows; beyond that the regions
# would describe a different paleogeography.
NEAREST_MA = 5.0


def nearest(maps, age):
    return min(maps, key=lambda item: (abs(item["age_ma"] - age), item["age_ma"]))


def gap_pairs(model, report, report_age, older_age, newer_age):
    span = abs(older_age - newer_age)
    pairs = []
    for piece in report["pieces"]:
        for region in piece.get("regions", []):
            if region["radius_deg"] < MIN_RADIUS_DEG:
                continue
            start = carry(model, region["plate"], region["centroid"], report_age, older_age)
            target = carry(model, region["plate"], region["centroid"], report_age, newer_age)
            if start is None or target is None:
                continue
            moved = separation(start, target)
            rate = moved / span if span else 0.0
            pairs.append({"lon": round(float(start[0]), 3), "lat": round(float(start[1]), 3),
                          "to_lon": round(float(target[0]), 3),
                          "to_lat": round(float(target[1]), 3),
                          "radius": region["radius_deg"], "moved": round(moved, 3),
                          "deg_per_ma": round(rate, 4),
                          "fast": rate > FASTEST_DEGREES_PER_MA,
                          "group": region["group"], "plate": region["plate"]})
    pairs.sort(key=lambda pair: pair["radius"], reverse=True)
    return pairs[:MAX_MOTIONS]


def main():
    atlas = json.loads(ATLAS.read_text())["maps"]
    grids = json.loads(GRIDS.read_text())["maps"]
    series = [item for item in atlas if item["age_ma"] > DEM_OLDEST_MA] + grids
    model = PackedModel(MODEL)
    reports = {}
    gaps = []
    borrowed = 0
    for older, newer in zip(series, series[1:]):
        source = nearest(atlas, older["age_ma"])
        if abs(source["age_ma"] - older["age_ma"]) > NEAREST_MA:
            raise SystemExit(f"No atlas map within {NEAREST_MA} Myr of {older['id']}.")
        if source["id"] not in reports:
            path = ATLAS_DERIVED / f"{source['id']}-pieces.json"
            if not path.exists():
                raise SystemExit(f"Missing {path}. Run scripts/segment_paleoatlas.py first.")
            reports[source["id"]] = json.loads(path.read_text())
        borrowed += source["age_ma"] != older["age_ma"]
        gaps.append({"from": older["id"], "to": newer["id"], "regions_from": source["id"],
                     "pairs": gap_pairs(model, reports[source["id"]], source["age_ma"],
                                        older["age_ma"], newer["age_ma"])})
    document = {"schema_version": 1, "model": MODEL,
                "catalogue": str(GRIDS.relative_to(ROOT)),
                "regions": str(ATLAS.relative_to(ROOT)),
                "method": ("Each gap borrows the plate-group regions of the 2016 atlas map "
                           "nearest its older end; every region's centroid is rotated back "
                           "to present-day coordinates with its dominant plate's PALEOMAP "
                           "rotation at that map's age, then forward to the gap's older and "
                           "newer ages."),
                "gaps": gaps}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(document, indent=1))
    counts = [len(gap["pairs"]) for gap in gaps]
    fastest = max((pair["deg_per_ma"] for gap in gaps for pair in gap["pairs"]), default=0.0)
    flagged = sum(pair["fast"] for gap in gaps for pair in gap["pairs"])
    print(f"{OUT.relative_to(ROOT)}: {len(gaps)} gaps, {sum(counts)} pairs "
          f"({min(counts)}-{max(counts)} per gap), {borrowed} gaps borrowing a map up to "
          f"{NEAREST_MA:g} Myr away, fastest {fastest:.2f} deg/Ma, {flagged} above "
          f"{FASTEST_DEGREES_PER_MA}")


if __name__ == "__main__":
    main()
