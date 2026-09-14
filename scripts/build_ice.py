#!/usr/bin/env python3
"""Rasterise ice onto the elevation series' texture grids, 2048 x 1024 equirectangular.

The present day, `paleodem-0000-ice.png`: red is grounded ice (Natural Earth glaciated
areas), green is floating shelf ice (Natural Earth Antarctic ice shelves), both 255
inside a polygon and 0 outside. Longitude and latitude map linearly to pixels, so no
reprojection is needed. Polygon parts are filled one by one; a part that is a hole is
filled as ice too, which affects a few nunataks and nothing else at this resolution.

Every older grid, `paleodem-<age>-ice.png`: red is the ice the 2016 PaleoAtlas paints on
the map nearest the grid's age, within 5 Myr and the younger map on a tie, as the names
and motions are borrowed; scripts/segment_paleoatlas.ice reads it, and the edge is
smoothed along longitude, wider toward the poles, so it does not break into spokes
where the texture's columns converge. Green stays empty, because the atlas draws one
white for sheet, shelf and sea ice alike. A grid whose map
paints no ice gets no file, so the overlay fades out across that gap, which there means
retreat. The atlas prelude older than 540 Ma gets none.

Check: the glacial deposits Cao et al. (2018) compiled, tillites and diamictites since
the Devonian, are rotated to each map's age with the PALEOMAP model and counted inside
the mask, within NEAR_DEGREES of it, inside a pale piece the latitude rule dropped, or
farther. The counts go to `ice-check.json` beside the masks and to stdout, for every map
read, so a map with deposits and no drawn ice shows up too. A deposit far from any drawn
ice, or inside a dropped piece, is worth a look; the compilation has nothing before the
Devonian, so the Ordovician goes unchecked.
"""
import argparse
import io
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import shapefile
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from atlas_motions import MODEL, PackedModel, carry  # noqa: E402
from segment_paleoatlas import cell_weights, ice, plate_raster  # noqa: E402

MANIFEST = ROOT / "sources/ice.json"
ATLAS = ROOT / "sources/paleomap-atlas-2016.json"
GRIDS = ROOT / "sources/paleodem-slices.json"
WIDTH, HEIGHT = 2048, 1024
NEAREST_MA = 5.0
NEAR_DEGREES = 5.0    # a deposit this close to the drawn edge counts as agreeing
DEPOSITS = ("PresentDay_LithData_Scotese2008_410-0Ma/"
            "PresentDay_GlacialDeposits_Scotese2008_410-0Ma.shp")


def rasterise(path, width=WIDTH, height=HEIGHT):
    image = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(image)
    reader = shapefile.Reader(str(path))
    for shape in reader.iterShapes():
        parts = list(shape.parts) + [len(shape.points)]
        for start, end in zip(parts, parts[1:]):
            ring = [((lon + 180.0) / 360.0 * width, (90.0 - lat) / 180.0 * height)
                    for lon, lat in shape.points[start:end]]
            if len(ring) >= 3:
                draw.polygon(ring, fill=255)
    return np.asarray(image)


def share(mask):
    """Share of the globe under a mask, in percent, cells weighted by area."""
    weights = cell_weights(*mask.shape)
    return float(weights[mask > 0].sum() / weights.sum()) * 100


def present(folders, out):
    grounded = rasterise(next(folders["glaciated"].glob("*.shp")))
    shelves = rasterise(next(folders["shelves"].glob("*.shp")))
    Image.fromarray(np.dstack([grounded, shelves, np.zeros_like(grounded)])).save(out / "paleodem-0000-ice.png")
    print(f"grounded ice {share(grounded):.2f}% of the globe, shelves {share(shelves):.2f}% -> paleodem-0000-ice.png")


def nearest(maps, age):
    return min(maps, key=lambda item: (abs(item["age_ma"] - age), item["age_ma"]))


def polar_smooth(mask, base_px=1.5, cap_px=80):
    """Blur along longitude, wider toward the poles, so the mask's edge stays soft on the globe.

    Every column of an equirectangular texture becomes a wedge at the pole, so the hard
    edge of a mask read from the atlas's one-degree cells turns into spokes when seen
    from above Antarctica. A Gaussian along each row whose width grows as 1/cos(latitude),
    about 0.15 degrees at the equator and capped at 8 degrees of longitude, averages the
    wedges into an edge the shader's smoothstep draws cleanly. The shape is unchanged
    where the columns are not squeezed.
    """
    height, width = mask.shape
    out = mask.astype(np.float32)
    latitude = 90.0 - (np.arange(height) + 0.5) / height * 180.0
    sigma = np.round(np.minimum(cap_px, base_px / np.maximum(np.cos(np.radians(latitude)), 1e-3)))
    for width_px in np.unique(sigma):
        rows = np.nonzero(sigma == width_px)[0]
        if width_px > 0:
            out[rows] = ndimage.gaussian_filter1d(out[rows], width_px, axis=1, mode="wrap")
    return np.clip(out, 0.0, 1.0)


def deposits(folder, model, width=3600, height=1800):
    """Every glacial deposit as (name, lon, lat, from_age, to_age, plate), the plate read
    from the PALEOMAP polygons at the present day, so the rotation is this project's."""
    reader = shapefile.Reader(str(next(folder.glob(f"**/{DEPOSITS}"))))
    fields = [field[0] for field in reader.fields[1:]]
    name, older, newer = (fields.index(key) for key in ("Formation", "FROMAGE", "TOAGE"))
    plates = plate_raster(model, 0.0, width, height)
    rows = []
    for entry in reader.iterShapeRecords():
        lon, lat = entry.shape.points[0]
        col = int((lon + 180.0) / 360.0 * width) % width
        row = min(height - 1, max(0, int((90.0 - lat) / 180.0 * height)))
        rows.append((str(entry.record[name]), lon, lat, float(entry.record[older]),
                     float(entry.record[newer]), int(plates[row, col])))
    return rows


def check(model, kept, dropped, points, age):
    """Where the deposits of `age` fall against the mask, after riding their plates there."""
    height, width = kept.shape
    # Distance to the drawn edge in degrees along a parallel at the equator; coarse, but
    # the deposits sit where a few degrees either way is the question.
    far = (ndimage.distance_transform_edt(~kept) * (360.0 / width) if kept.any()
           else np.full(kept.shape, np.inf))
    counts = {"deposits": 0, "inside": 0, "near": 0, "dropped": 0, "outside": 0, "unrotated": 0}
    listed = []
    for name, lon, lat, older, newer, plate in points:
        if not newer <= age <= older:
            continue
        counts["deposits"] += 1
        moved = carry(model, plate, (lon, lat), 0.0, age) if plate else None
        if moved is None:
            counts["unrotated"] += 1
            continue
        col = int((moved[0] + 180.0) % 360.0 / 360.0 * width) % width
        row = min(height - 1, max(0, int((90.0 - moved[1]) / 180.0 * height)))
        if kept[row, col]:
            verdict = "inside"
        elif dropped[row, col]:
            verdict = "dropped"
        elif far[row, col] <= NEAR_DEGREES:
            verdict = "near"
        else:
            verdict = "outside"
        counts[verdict] += 1
        if verdict in ("dropped", "outside"):
            listed.append({"name": name, "lon": round(float(moved[0]), 1), "lat": round(float(moved[1]), 1),
                           "verdict": verdict,
                           "degrees_from_ice": None if np.isinf(far[row, col]) else round(float(far[row, col]), 1)})
    return counts, listed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=ROOT / "data/derived/paleodem", type=Path)
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text())
    folders = {asset["unzip"]: (ROOT / asset["path"]).parent / asset["unzip"] for asset in manifest["assets"]}
    args.out.mkdir(parents=True, exist_ok=True)
    present(folders, args.out)

    atlas = json.loads(ATLAS.read_text())
    maps = atlas["maps"]
    model = PackedModel(MODEL)
    points = deposits(folders["glacial"], model)
    masks, report = {}, {}
    written = borrowed = 0
    with zipfile.ZipFile(ROOT / atlas["archive"]["path"]) as bundle:
        for item in json.loads(GRIDS.read_text())["maps"]:
            if item["age_ma"] == 0:
                continue
            source = nearest(maps, item["age_ma"])
            if abs(source["age_ma"] - item["age_ma"]) > NEAREST_MA:
                raise SystemExit(f"No atlas map within {NEAREST_MA} Myr of {item['id']}.")
            if source["id"] not in masks:
                rgb = np.asarray(Image.open(io.BytesIO(bundle.read(source["member"])))
                                 .convert("RGB")).astype(np.float32)
                kept, dropped = ice(rgb)
                masks[source["id"]] = kept
                counts, listed = check(model, kept, dropped, points, source["age_ma"])
                if kept.any() or counts["deposits"]:
                    report[source["id"]] = {"age_ma": source["age_ma"], "ice_share": round(share(kept), 2),
                                            "dropped_share": round(share(dropped), 2), **counts, "listed": listed}
            target = args.out / f"{item['id']}-ice.png"
            kept = masks[source["id"]]
            if not kept.any():
                target.unlink(missing_ok=True)
                continue
            red = np.asarray(Image.fromarray((polar_smooth(kept) * 255).astype(np.uint8))
                             .resize((WIDTH, HEIGHT), Image.BILINEAR))
            Image.fromarray(np.dstack([red, np.zeros_like(red), np.zeros_like(red)])).save(target)
            written += 1
            borrowed += source["age_ma"] != item["age_ma"]
    (args.out / "ice-check.json").write_text(json.dumps({
        "deposits": manifest["assets"][2]["cite"], "near_degrees": NEAR_DEGREES,
        "method": ("Glacial deposits at present-day coordinates ride the PALEOMAP plate under them "
                   "to each map's age and are counted against the ice the atlas paints there: inside "
                   "the mask, within near_degrees of its edge, inside a pale piece the latitude rule "
                   "dropped, or farther."),
        "maps": report}, indent=1))
    print(f"{written} grids given the atlas's ice ({borrowed} borrowing a map at another age), "
          f"{len(report)} maps read; {len(points)} deposits in the check -> ice-check.json")
    for map_id, row in report.items():
        print(f"  {map_id} {row['age_ma']:6g} Ma  ice {row['ice_share']:5.2f}%  deposits {row['deposits']:3d}: "
              f"inside {row['inside']} near {row['near']} dropped {row['dropped']} "
              f"outside {row['outside']} unrotated {row['unrotated']}")


if __name__ == "__main__":
    main()
