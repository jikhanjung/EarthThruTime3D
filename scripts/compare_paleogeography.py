#!/usr/bin/env python3
"""Compare land from other palaeogeographies with the 2016 PaleoAtlas masks.

A review, not a pipeline: it reads two archives under data/sources/paleogeography/ and
the masks under data/derived/paleoatlas/, and reports how much land they share at the
same ages.

- PaleoCoastlines v7.1 (Kocsis & Scotese 2021): coastline polygons already in
  reconstructed coordinates, from the PALEOMAP DEMs but moved to the maximum
  transgression that marine fossils in the Paleobiology Database indicate.
- Cao et al. 2017: Golonka's palaeogeography revised with marine fossils and
  reconstructed in the Matthews et al. 2016 plate model, as GeoTIFFs. Land is the
  landmass and mountain classes; shallow marine counts as sea, as in our masks.

For each pair the report gives the overlap (area-weighted intersection over union), the
spin-axis shift that maximises it, and both land fractions. A spin-axis shift is the
freedom palaeomagnetism leaves open, so a large best shift is a longitude disagreement
rather than a different picture.
"""
import io
import json
import sys
import tempfile
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from pack_plates import shapefile_rings  # noqa: E402

SOURCES = ROOT / "data/sources/paleogeography"
ATLAS = json.loads((ROOT / "sources/paleomap-atlas-2016.json").read_text())["maps"]
ATLAS_DIR = ROOT / "data/derived/paleoatlas"
OUT = ROOT / "data/derived/comparison"
COASTLINES_ZIP = SOURCES / "paleocoastlines2021/PaleoCoastlines_v7.1.zip"
CAO_ZIP = SOURCES / "cao2017/Cao_etal_2017_BG_Supplement.zip"
WIDTH, HEIGHT = 720, 360
NEAREST_MA = 3.0     # a pair of maps further apart than this in age is not compared

WEIGHTS = (np.cos(np.radians(90 - (np.arange(HEIGHT) + 0.5) / HEIGHT * 180))[:, None]
           * np.ones((1, WIDTH)))

# Cao et al. 2017 GeoTIFF palette, read from the rasters.
CAO_LAND = [(255, 255, 0), (255, 165, 0)]          # landmass, mountain
CAO_ICE = [(255, 255, 255)]                         # ice sheet, where drawn
CAO_LINES = (153, 153, 153)                         # present-day coastlines, terranes


def overlap(first, second):
    union = (WEIGHTS * (first | second)).sum()
    return float((WEIGHTS * (first & second)).sum() / union) if union else 0.0


def best_shift(moving, fixed, step_px=1):
    scores = [overlap(np.roll(moving, shift, axis=1), fixed)
              for shift in range(-WIDTH // 2, WIDTH // 2, step_px)]
    index = int(np.argmax(scores))
    return (index * step_px - WIDTH // 2) * 360.0 / WIDTH, scores[index], scores[WIDTH // 2]


def fraction(land):
    return float((WEIGHTS * land).sum() / WEIGHTS.sum())


def atlas_land(item):
    field = Image.open(ATLAS_DIR / f"{item['id']}-field.png").resize((WIDTH, HEIGHT), Image.BILINEAR)
    return np.asarray(field) > 128


def rasterise_parts(records):
    """Even-odd fill, so holes in a polygon stay open."""
    canvas = Image.new("1", (WIDTH, HEIGHT), 0)
    for parts in records:
        for ring in parts:
            if len(ring) < 3:
                continue
            layer = Image.new("1", (WIDTH, HEIGHT), 0)
            ImageDraw.Draw(layer).polygon(
                [((lon + 180) / 360 * WIDTH, (90 - lat) / 180 * HEIGHT) for lon, lat in ring], fill=1)
            canvas = ImageChops.logical_xor(canvas, layer)
    return np.asarray(canvas, dtype=bool)


def coastline_maps():
    maps = {}
    with zipfile.ZipFile(COASTLINES_ZIP) as bundle, tempfile.TemporaryDirectory() as tmp:
        names = [name for name in bundle.namelist() if name.startswith("Data/CS/")]
        bundle.extractall(tmp, members=names)
        for shp in sorted(Path(tmp, "Data/CS").glob("*Ma_CS_v7.shp")):
            age = float(shp.name.split("Ma_")[0])
            maps[age] = rasterise_parts(shapefile_rings(shp))
    return maps


def cao_maps():
    Image.MAX_IMAGE_PIXELS = None
    maps = {}
    with zipfile.ZipFile(CAO_ZIP) as bundle:
        for name in bundle.namelist():
            if "__MACOSX" in name or not name.endswith("Ma.tiff") or "GeoTiffs/" not in name:
                continue
            age = float(name.rsplit("_", 1)[1].removesuffix("Ma.tiff"))
            rgb = np.asarray(Image.open(io.BytesIO(bundle.read(name))).convert("RGB"))
            lines = np.all(rgb == CAO_LINES, axis=-1)
            if lines.any():
                _, index = ndimage.distance_transform_edt(lines, return_indices=True)
                rgb = rgb[tuple(index)]
            land = np.zeros(rgb.shape[:2], dtype=bool)
            for colour in CAO_LAND + CAO_ICE:
                land |= np.all(rgb == colour, axis=-1)
            small = Image.fromarray((land * 255).astype(np.uint8)).resize((WIDTH, HEIGHT), Image.BOX)
            maps[age] = np.asarray(small) >= 128
    return maps


def nearest(maps, age):
    best = min(maps, key=lambda key: abs(key - age))
    return (best, maps[best]) if abs(best - age) <= NEAREST_MA else (None, None)


def side_by_side(name, panels):
    """Stack labelled equirectangular panels: land tan, sea blue."""
    rows = []
    for title, land in panels:
        image = np.where(land[..., None], [205, 193, 148], [22, 86, 135]).astype(np.uint8)
        tile = Image.fromarray(image).resize((WIDTH, HEIGHT))
        ImageDraw.Draw(tile).text((6, 4), title, fill=(255, 255, 255))
        rows.append(tile)
    sheet = Image.new("RGB", (WIDTH, HEIGHT * len(rows)))
    for index, tile in enumerate(rows):
        sheet.paste(tile, (0, index * HEIGHT))
    sheet.save(OUT / name)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    coast = coastline_maps()
    cao = cao_maps()
    atlas = {item["age_ma"]: item for item in ATLAS if item["id"] != "paleoatlas-lgm"}
    rows = []
    print(f"PaleoCoastlines: {len(coast)} ages {min(coast):g}-{max(coast):g} Ma; "
          f"Cao 2017: {len(cao)} ages {min(cao):g}-{max(cao):g} Ma")
    print(f"\n{'age':>5} {'pair':34} {'dAge':>5} {'IoU@0':>6} {'shift':>7} {'IoU':>6} "
          f"{'land A':>7} {'land B':>7}")
    for age in sorted(atlas):
        ours = atlas_land(atlas[age])
        for label, maps in (("PaleoCoastlines vs atlas", coast), ("Cao 2017 vs atlas", cao)):
            other_age, other = nearest(maps, age)
            if other is None:
                continue
            shift, best, at_zero = best_shift(other, ours)
            row = {"age": age, "pair": label, "other_age": other_age, "iou_at_zero": round(at_zero, 3),
                   "best_shift_deg": shift, "best_iou": round(best, 3),
                   "land_other": round(fraction(other), 3), "land_atlas": round(fraction(ours), 3)}
            rows.append(row)
            print(f"{age:5g} {label:34} {other_age - age:+5g} {at_zero:6.3f} {shift:+6.1f}° "
                  f"{best:6.3f} {row['land_other']:7.3f} {row['land_atlas']:7.3f}")
    for age in (0.0, 90.0, 255.0, 400.0):
        ours = atlas_land(atlas[min(atlas, key=lambda key: abs(key - age))])
        panels = [(f"2016 PaleoAtlas mask {age:g} Ma", ours)]
        for label, maps in (("PaleoCoastlines", coast), ("Cao 2017 (Matthews 2016 frame)", cao)):
            other_age, other = nearest(maps, age)
            if other is not None:
                panels.append((f"{label} {other_age:g} Ma", other))
        side_by_side(f"compare-{int(age):03d}.png", panels)
    (OUT / "paleogeography-comparison.json").write_text(json.dumps(rows, indent=1))
    print(f"\nWrote {OUT.relative_to(ROOT)}/paleogeography-comparison.json and compare-*.png")


if __name__ == "__main__":
    main()
