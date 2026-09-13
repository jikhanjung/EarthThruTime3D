#!/usr/bin/env python3
"""Test land/sea maps against where the Paleobiology Database found marine and land fossils.

A marine fossil sitting on a map's land, or a land fossil in its sea, is a disagreement
between the map and the rock record. This counts them for three palaeogeographies:

- the 2016 PaleoAtlas masks (data/derived/paleoatlas), PALEOMAP frame;
- PaleoCoastlines v7.1 (Kocsis & Scotese 2021), PALEOMAP frame;
- Cao et al. 2017 revised maps, Matthews et al. 2016 frame.

Fossils are placed with the same plate model as the map they are tested against: each
collection's present-day position gets the plate id of the model polygon that contains it
at that age, and that plate's rotation takes it to the map's age. A collection is used
only if its age range is narrow enough to belong to one map.

PaleoCoastlines and Cao et al. were both fitted to Paleobiology Database collections, so
testing them with the same records is partly in-sample. Every collection carries its
creation date, so each result is also reported for collections created after the dataset
was built, which neither dataset has seen.
"""
import csv
import io
import json
import sys
import tempfile
import zipfile
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from measure_longitude_offsets import PackedModel  # noqa: E402
from pack_plates import shapefile_rings  # noqa: E402
from rotation_model import rotate  # noqa: E402

PBDB = ROOT / "data/sources/paleogeography/pbdb/collections.csv"
ATLAS = json.loads((ROOT / "sources/paleomap-atlas-2016.json").read_text())["maps"]
ATLAS_DIR = ROOT / "data/derived/paleoatlas"
COASTLINES_ZIP = ROOT / "data/sources/paleogeography/paleocoastlines2021/PaleoCoastlines_v7.1.zip"
CAO_ZIP = ROOT / "data/sources/paleogeography/cao2017/Cao_etal_2017_BG_Supplement.zip"
OUT = ROOT / "data/derived/comparison/fossil-check.json"

# Grid for land rasters and distance to the coast: 0.1 degree.
WIDTH, HEIGHT = 3600, 1800
DEG_PER_PX = 360.0 / WIDTH
TOLERANCE_DEG = 1.0          # about 110 km: reconstruction and mapping error both reach this far
MAX_AGE_SPAN_MA = 15.0       # a collection dated more loosely than this belongs to no single map

# The datasets were built from Paleobiology Database downloads made before these dates.
CAO_DOWNLOAD = "2016-09-07"
COASTLINES_BUILT = "2020-11-26"

# Operator decision: PBDB environment terms that are unambiguously marine or unambiguously
# non-marine. Marginal settings (coastal, estuary, lagoon, delta plain, paralic) sit on the
# line these maps draw and are left out rather than forced to a side.
MARINE = {
    "marine indet.", "carbonate indet.", "peritidal", "shallow subtidal indet.",
    "open shallow subtidal", "lagoonal/restricted shallow subtidal", "sand shoal",
    "reef, buildup or bioherm", "perireef or subreef", "intrashelf/intraplatform reef",
    "platform/shelf-margin reef", "slope/ramp reef", "basin reef", "deep subtidal ramp",
    "deep subtidal shelf", "deep subtidal indet.", "offshore ramp", "offshore shelf",
    "offshore indet.", "slope", "basinal (carbonate)", "basinal (siliceous)",
    "shoreface", "transition zone/lower shoreface", "offshore", "submarine fan",
    "basinal (siliciclastic)", "deep-water indet.", "delta front", "prodelta",
    "foreshore",
}
TERRESTRIAL = {
    "terrestrial indet.", "fluvial indet.", "alluvial fan", "channel lag",
    # PBDB spells two of these with literal quotation marks.
    "coarse channel fill", "fine channel fill", '"channel"', "wet floodplain",
    "dry floodplain", '"floodplain"', "crevasse splay", "levee", "mire/swamp",
    "fluvial-lacustrine indet.", "lacustrine - large", "lacustrine - small", "pond",
    "crater lake", "lacustrine delta plain", "lacustrine interdistributary bay",
    "lacustrine delta front", "lacustrine prodelta", "lacustrine deltaic indet.",
    "lacustrine indet.", "dune", "interdune", "loess", "eolian indet.", "cave",
    "fissure fill", "sinkhole", "karst indet.", "tar", "spring", "glacial",
    "fluvial-deltaic indet.", "deltaic indet.", "delta plain", "interdistributary bay",
}


def load_collections():
    rows = []
    with PBDB.open(newline="", encoding="utf-8", errors="replace") as handle:
        for record in csv.DictReader(handle):
            environment = (record.get("environment") or "").strip()
            kind = "marine" if environment in MARINE else "land" if environment in TERRESTRIAL else None
            if kind is None:
                continue
            try:
                lon, lat = float(record["lng"]), float(record["lat"])
                oldest, youngest = float(record["max_ma"]), float(record["min_ma"])
            except (TypeError, ValueError):
                continue
            if oldest - youngest > MAX_AGE_SPAN_MA:
                continue
            rows.append((lon, lat, (oldest + youngest) / 2, oldest, youngest, kind,
                         (record.get("created") or "")[:10]))
    return rows


def rasterise_plates(model, age):
    """Plate id at each present-day cell, from the model polygons valid at `age`."""
    canvas = Image.new("I", (WIDTH, HEIGHT), 0)
    draw = ImageDraw.Draw(canvas)
    for feature in model.shapes:
        if not feature["to"] - 1e-9 <= age <= feature["from"] + 1e-9:
            continue
        for ring in feature["rings"]:
            points = [((ring[i] + 180) / 360 * WIDTH, (90 - ring[i + 1]) / 180 * HEIGHT)
                      for i in range(0, len(ring), 2)]
            if len(points) >= 3:
                draw.polygon(points, fill=int(feature["pid"]))
    return np.asarray(canvas, dtype=np.int32)


def cell(lon, lat):
    col = int(np.clip((lon + 180) / 360 * WIDTH, 0, WIDTH - 1))
    row = int(np.clip((90 - lat) / 180 * HEIGHT, 0, HEIGHT - 1))
    return row, col


def signed_distance(land):
    """Degrees from the coast, positive on land, negative at sea, wrapping in longitude."""
    wide = np.tile(land, (1, 3))
    inside = ndimage.distance_transform_edt(wide)[:, WIDTH:2 * WIDTH].astype(np.float32)
    outside = ndimage.distance_transform_edt(~wide)[:, WIDTH:2 * WIDTH].astype(np.float32)
    return (inside - outside) * np.float32(DEG_PER_PX)


def place(collections, model, map_age, select):
    """Reconstruct the collections `select` keeps to `map_age` with `model`."""
    plates = rasterise_plates(model, map_age)
    placed, unplaced = [], 0
    for lon, lat, mid, oldest, youngest, kind, created in collections:
        if not select(mid, oldest, youngest):
            continue
        plate = int(plates[cell(lon, lat)])
        turn = model.rotation(plate, map_age) if plate else None
        if turn is None:
            unplaced += 1
            continue
        paleo_lon, paleo_lat = rotate(turn, lon, lat)
        placed.append((paleo_lon, paleo_lat, kind, created))
    return placed, unplaced


def score(placed, distance, built=None):
    counts = defaultdict(int)
    for lon, lat, kind, created in placed:
        if built and created <= built:
            continue
        depth = distance[cell(lon, lat)]
        counts[f"{kind}_n"] += 1
        wrong = depth > 0 if kind == "marine" else depth < 0
        wrong_far = depth > TOLERANCE_DEG if kind == "marine" else depth < -TOLERANCE_DEG
        counts[f"{kind}_wrong"] += int(wrong)
        counts[f"{kind}_wrong_beyond_tolerance"] += int(wrong_far)
    return dict(counts)


def atlas_distance(item):
    field = np.asarray(Image.open(ATLAS_DIR / f"{item['id']}-field.png").resize((WIDTH, HEIGHT), Image.BILINEAR))
    return signed_distance(field > 128)


def coastline_distances():
    """One age at a time: holding all 81 grids at once ran the machine out of memory."""
    with zipfile.ZipFile(COASTLINES_ZIP) as bundle, tempfile.TemporaryDirectory() as tmp:
        bundle.extractall(tmp, members=[name for name in bundle.namelist() if name.startswith("Data/CS/")])
        for shp in Path(tmp, "Data/CS").glob("*Ma_CS_v7.shp"):
            canvas = Image.new("1", (WIDTH, HEIGHT), 0)
            for parts in shapefile_rings(shp):
                for ring in parts:
                    if len(ring) < 3:
                        continue
                    layer = Image.new("1", (WIDTH, HEIGHT), 0)
                    ImageDraw.Draw(layer).polygon(
                        [((lon + 180) / 360 * WIDTH, (90 - lat) / 180 * HEIGHT) for lon, lat in ring], fill=1)
                    canvas = ImageChops.logical_xor(canvas, layer)
            yield float(shp.name.split("Ma_")[0]), signed_distance(np.asarray(canvas, dtype=bool))


# Cao et al. 2017 intervals: (oldest, youngest, reconstruction age), from the supplement README.
CAO_INTERVALS = [(11, 2, 6), (20, 11, 14), (29, 20, 22), (37, 29, 33), (49, 37, 45), (58, 49, 53),
                 (81, 58, 76), (94, 81, 90), (117, 94, 105), (135, 117, 126), (146, 135, 140),
                 (166, 146, 152), (179, 166, 169), (203, 179, 195), (224, 203, 218),
                 (248, 224, 232), (269, 248, 255), (285, 269, 277), (296, 285, 287),
                 (323, 296, 302), (338, 323, 328), (359, 338, 348), (380, 359, 368),
                 (402, 380, 396)]


def cao_distance(age):
    Image.MAX_IMAGE_PIXELS = None
    with zipfile.ZipFile(CAO_ZIP) as bundle:
        name = next(n for n in bundle.namelist() if "__MACOSX" not in n
                    and n.endswith(f"_{age}Ma.tiff") and "GeoTiffs/" in n)
        rgb = np.asarray(Image.open(io.BytesIO(bundle.read(name))).convert("RGB"))
    lines = np.all(rgb == (153, 153, 153), axis=-1)
    if lines.any():
        _, index = ndimage.distance_transform_edt(lines, return_indices=True)
        rgb = rgb[tuple(index)]
    land = np.zeros(rgb.shape[:2], dtype=bool)
    for colour in ((255, 255, 0), (255, 165, 0), (255, 255, 255)):
        land |= np.all(rgb == colour, axis=-1)
    small = np.asarray(Image.fromarray((land * 255).astype(np.uint8)).resize((WIDTH, HEIGHT), Image.BOX)) >= 128
    return signed_distance(small)


def summarise(label, rows, key="all"):
    total = defaultdict(int)
    for row in rows:
        for name, value in row[key].items():
            total[name] += value
    def share(kind, which):
        n = total.get(f"{kind}_n", 0)
        return (total.get(f"{kind}_{which}", 0) / n) if n else float("nan")
    print(f"  {label:44} marine {total.get('marine_n', 0):6d}: on land {share('marine', 'wrong'):6.1%}, "
          f">1° inland {share('marine', 'wrong_beyond_tolerance'):6.1%} | land {total.get('land_n', 0):5d}: "
          f"at sea {share('land', 'wrong'):6.1%}, >1° offshore {share('land', 'wrong_beyond_tolerance'):6.1%}")
    return dict(total)


def main():
    collections = load_collections()
    print(f"{len(collections)} dated marine or land collections from {PBDB.relative_to(ROOT)}")
    paleomap = PackedModel("paleomap2016")
    matthews = PackedModel("matthews2016")
    results = {"atlas": [], "coastlines": [], "cao": []}

    for item in ATLAS:
        if item["id"] == "paleoatlas-lgm":
            continue
        age = item["age_ma"]
        placed, unplaced = place(collections, paleomap, age,
                                 lambda mid, old, young, age=age: abs(mid - age) <= 2.5)
        results["atlas"].append({"age": age, "unplaced": unplaced,
                                 "all": score(placed, atlas_distance(item))})

    for age, distance in coastline_distances():
        placed, unplaced = place(collections, paleomap, age,
                                 lambda mid, old, young, age=age: abs(mid - age) <= 2.5)
        results["coastlines"].append({"age": age, "unplaced": unplaced,
                                      "all": score(placed, distance),
                                      "after_build": score(placed, distance, COASTLINES_BUILT)})

    for oldest, youngest, age in CAO_INTERVALS:
        placed, unplaced = place(collections, matthews, float(age),
                                 lambda mid, old, young, o=oldest, y=youngest: y <= mid <= o)
        distance = cao_distance(age)
        results["cao"].append({"age": age, "unplaced": unplaced,
                               "all": score(placed, distance),
                               "after_download": score(placed, distance, CAO_DOWNLOAD)})

    results["coastlines"].sort(key=lambda row: row["age"])
    print("\nAll ages each dataset covers:")
    summary = {
        "atlas": summarise("2016 PaleoAtlas masks, 0-750 Ma", results["atlas"]),
        "coastlines": summarise("PaleoCoastlines v7.1, 0-535 Ma", results["coastlines"]),
        "coastlines_after_build": summarise(f"  collections created after {COASTLINES_BUILT}",
                                            results["coastlines"], "after_build"),
        "cao": summarise("Cao et al. 2017, 402-2 Ma", results["cao"]),
        "cao_after_download": summarise(f"  collections created after {CAO_DOWNLOAD}",
                                        results["cao"], "after_download"),
    }
    print("\nSame window for all three, 402-2 Ma:")
    window = {name: [row for row in rows if 2 <= row["age"] <= 402] for name, rows in results.items()}
    summary["window_402_2"] = {
        "atlas": summarise("2016 PaleoAtlas masks", window["atlas"]),
        "coastlines": summarise("PaleoCoastlines v7.1", window["coastlines"]),
        "cao": summarise("Cao et al. 2017", window["cao"]),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"tolerance_deg": TOLERANCE_DEG, "max_age_span_ma": MAX_AGE_SPAN_MA,
                               "summary": summary, "by_age": results}, indent=1))
    print(f"\nWrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
