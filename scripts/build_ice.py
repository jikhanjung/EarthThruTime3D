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

Where the atlas paints nothing but the land-ice volume of van der Meer et al. (2022) is
at least ICE_VOLUME_MKM3, the cut the sea-level strip already shades, the grid gets a
cap instead: everything poleward of the same paper's ice latitude for that age, both
hemispheres, the edge eased over two degrees. It is a modelled limit, not an outline,
and `ice-sources.json` beside the masks says for every grid whether its mask is
natural-earth, atlas or limit, so the page can say so too.

Red is not a mask but a signed distance to the ice edge, 128 at the edge and
ICE_FIELD_SCALE levels per degree, positive inside, so the shader can cut it at a level
other than the edge: the sea-level control moves the cut, and the ice grows or shrinks
with it. How far per metre is one number per grid, written beside the masks: a metre of
sea level is 1/SEA_PER_MKM3 million km3 of ice (the paper's ratio), a sheet's area goes
as its volume to the AREA_EXPONENT, and the edge moves by the area change divided by
the perimeter. A uniform advance is a toy, real sheets grow from centres, but at the
present it puts the sheets at about 8% of the globe for the 130 m of the last glacial
maximum, against the 11% the atlas paints then with sea ice included.

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
import openpyxl
import shapefile
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from atlas_motions import MODEL, PackedModel, carry  # noqa: E402
from segment_paleoatlas import cell_weights, ice, plate_raster  # noqa: E402

MANIFEST = ROOT / "sources/ice.json"
SEALEVEL = ROOT / "sources/sealevel.json"
ICE_VOLUME_MKM3 = 5.0                        # the strip's cut: a fifth of today's land ice
ICE_FIELD_SCALE = 8.0                        # levels per degree in the red channel, 128 at the edge
SEA_PER_MKM3 = 2.5                           # metres of sea level per million km3 of ice, the paper's ratio
AREA_EXPONENT = 0.8                          # a sheet's area goes as its volume to this power
EARTH_KM2 = 510.1e6
KM_PER_DEGREE = 111.2
ICE_LAT_COLUMN, ICE_VOLUME_COLUMN = 13, 22   # IceLat_degrees AVG, VolLandice_km3 AVG in Supplementary Table 1
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


def present(folders):
    grounded = rasterise(next(folders["glaciated"].glob("*.shp")))
    shelves = rasterise(next(folders["shelves"].glob("*.shp")))
    print(f"grounded ice {share(grounded):.2f}% of the globe, shelves {share(shelves):.2f}% -> paleodem-0000-ice.png")
    return grounded, shelves


def distance_field(red):
    """The soft mask as a signed distance to its edge, in degrees, encoded around 128."""
    inside = red >= 128
    height, width = inside.shape
    degrees = 360.0 / width      # the grid is square in degrees, so one figure serves both axes
    signed = (ndimage.distance_transform_edt(inside) - ndimage.distance_transform_edt(~inside)) * degrees
    return np.clip(128.0 + signed * ICE_FIELD_SCALE, 0, 255).astype(np.uint8)


def edge_rate(red, volume_mkm3):
    """How far the ice edge moves per metre of sea level, in the red channel's units.

    A metre of sea level is 1/SEA_PER_MKM3 million km3 of ice; a sheet's area goes as
    volume to the AREA_EXPONENT, so d(area) = AREA_EXPONENT * area / volume * d(volume);
    the edge moves by the area change over the perimeter. The perimeter is counted on the
    raster, one pixel's width per boundary pixel, which overstates a ragged edge; the
    number is a rate for a what-if, not a measurement.
    """
    inside = red >= 128
    if volume_mkm3 <= 0 or not inside.any():
        return 0.0
    height, width = inside.shape
    weights = cell_weights(height, width)
    area_km2 = float(weights[inside].sum() / weights.sum()) * EARTH_KM2
    boundary = inside & ~ndimage.binary_erosion(inside)
    latitude = 90.0 - (np.arange(height) + 0.5) / height * 180.0
    across = KM_PER_DEGREE * 360.0 / width * np.cos(np.radians(latitude))
    along = KM_PER_DEGREE * 180.0 / height
    perimeter_km = float(((across + along) / 2.0)[:, None].repeat(width, axis=1)[boundary].sum())
    area_per_metre = AREA_EXPONENT * area_km2 / volume_mkm3 / SEA_PER_MKM3
    degrees_per_metre = area_per_metre / perimeter_km / KM_PER_DEGREE
    return degrees_per_metre * ICE_FIELD_SCALE / 255.0


def nearest(maps, age):
    return min(maps, key=lambda item: (abs(item["age_ma"] - age), item["age_ma"]))


def paper():
    """van der Meer et al. (2022) per Myr: age -> (ice latitude limit in degrees, land ice in Mkm3)."""
    manifest = json.loads(SEALEVEL.read_text())
    path = next(ROOT / asset["path"] for asset in manifest["assets"] if asset["path"].endswith("mmc1.xlsx"))
    sheet = openpyxl.load_workbook(path, read_only=True, data_only=True).worksheets[0]
    rows = list(sheet.iter_rows(values_only=True))
    if rows[2][ICE_LAT_COLUMN] != "IceLat_degrees" or rows[2][ICE_VOLUME_COLUMN] != "VolLandice_km3":
        raise SystemExit(f"Unexpected column layout in {path.name}")
    return {int(row[0]): (float(row[ICE_LAT_COLUMN]), float(row[ICE_VOLUME_COLUMN]) / 1e6)
            for row in rows[4:] if isinstance(row[0], (int, float))}


def limit_cap(latitude_limit, width=WIDTH, height=HEIGHT):
    """A cap poleward of the paper's ice latitude in both hemispheres, eased over two degrees."""
    latitude = 90.0 - (np.arange(height) + 0.5) / height * 180.0
    edge = np.clip((np.abs(latitude) - (latitude_limit - 1.0)) / 2.0, 0.0, 1.0)
    return np.repeat(edge[:, None], width, axis=1)


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
    reference = paper()
    grounded, shelves = present(folders)
    Image.fromarray(np.dstack([distance_field(grounded), shelves, np.zeros_like(grounded)])).save(
        args.out / "paleodem-0000-ice.png")
    today = reference[0][1]
    rates = {"paleodem-0000": edge_rate(grounded, today)}
    # The anchor: the present sheets grown for the last glacial maximum's 130 m, by the
    # same power law, against what the atlas paints at the LGM (sea ice included).
    grown = share(grounded) * ((today + 130.0 / SEA_PER_MKM3) / today) ** AREA_EXPONENT
    print(f"check: at -130 m the present sheets would cover {grown:.1f}% of the globe; "
          "the atlas paints 11.1% at the last glacial maximum, sea ice included")

    atlas = json.loads(ATLAS.read_text())
    maps = atlas["maps"]
    model = PackedModel(MODEL)
    points = deposits(folders["glacial"], model)
    masks, report = {}, {}
    sources = {"paleodem-0000": "natural-earth"}
    written = borrowed = capped = 0
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
            if kept.any():
                red = np.asarray(Image.fromarray((polar_smooth(kept) * 255).astype(np.uint8))
                                 .resize((WIDTH, HEIGHT), Image.BILINEAR))
                sources[item["id"]] = "atlas"
                written += 1
                borrowed += source["age_ma"] != item["age_ma"]
            else:
                limit, volume = reference.get(int(round(item["age_ma"])), (None, 0.0))
                if limit is None or volume < ICE_VOLUME_MKM3:
                    target.unlink(missing_ok=True)
                    continue
                red = (limit_cap(limit) * 255).astype(np.uint8)
                sources[item["id"]] = "limit"
                capped += 1
            rates[item["id"]] = edge_rate(red, reference.get(int(round(item["age_ma"])), (None, 0.0))[1])
            field = distance_field(red)
            Image.fromarray(np.dstack([field, np.zeros_like(field), np.zeros_like(field)])).save(target)
    (args.out / "ice-check.json").write_text(json.dumps({
        "deposits": manifest["assets"][2]["cite"], "near_degrees": NEAR_DEGREES,
        "method": ("Glacial deposits at present-day coordinates ride the PALEOMAP plate under them "
                   "to each map's age and are counted against the ice the atlas paints there: inside "
                   "the mask, within near_degrees of its edge, inside a pale piece the latitude rule "
                   "dropped, or farther."),
        "maps": report}, indent=1))
    (args.out / "ice-sources.json").write_text(json.dumps({
        "method": ("Where each grid's ice mask came from: natural-earth for the present; atlas for the "
                   "2016 PaleoAtlas's white read by segment_paleoatlas.ice; limit for a cap poleward of "
                   "the ice latitude of van der Meer et al. (2022), drawn where the atlas paints nothing "
                   f"but the paper's land-ice volume is at least {ICE_VOLUME_MKM3:g} million km3, the "
                   "sea-level strip's own cut."),
        "rates_method": ("How far each grid's ice edge moves per metre of sea level, in the red channel's "
                         f"units ({ICE_FIELD_SCALE:g} levels per degree over 255): a metre of sea level is "
                         f"1/{SEA_PER_MKM3:g} million km3 of ice, area goes as volume to the {AREA_EXPONENT:g}, "
                         "and the edge moves by the area change over the perimeter. The shader cuts the "
                         "field at 0.5 + rate * offset."),
        "grids": sources, "rates": {key: round(value, 7) for key, value in rates.items()}}, indent=1))
    print(f"{written} grids given the atlas's ice ({borrowed} borrowing a map at another age), "
          f"{capped} a cap at the paper's limit, {len(report)} maps read; "
          f"{len(points)} deposits in the check -> ice-check.json, ice-sources.json")
    for map_id, row in report.items():
        print(f"  {map_id} {row['age_ma']:6g} Ma  ice {row['ice_share']:5.2f}%  deposits {row['deposits']:3d}: "
              f"inside {row['inside']} near {row['near']} dropped {row['dropped']} "
              f"outside {row['outside']} unrotated {row['unrotated']}")


if __name__ == "__main__":
    main()
