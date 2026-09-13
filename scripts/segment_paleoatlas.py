#!/usr/bin/env python3
"""Separate land from sea in the PALEOMAP PaleoAtlas (2016) rasters.

Same purpose as scripts/segment_landmass.py, for a different source: the 2016 atlas maps
are equirectangular, carry no frame or lettering, and are the same edition as the
PALEOMAP rotation model. The 2002 web-map masks stay as they are; these land in
data/derived/paleoatlas/ so the two can be compared.

What counts as land is an operator decision, recorded here:
- Anything painted blue is sea, deep ocean and continental shelf alike, matching the
  2002 masks.
- Pale white is ice. It counts as land only inside the PALEOMAP continental polygons for
  that age, so an ice sheet is land and sea ice is not. This is the one place the masks
  lean on the plate model, and it makes floating ice shelves such as the Ross sea.
- Thin black boundary lines and the red credit are drawn over the map; they are removed
  and refilled from neighbouring map colour, so a coast under a line is interpolated.

Names come from the plate model, not the map: each piece is split into regions by which
PALEOMAP plate group lies under it (annotations/paleomap-plate-groups.json), and the
largest region of each group carries that group's name. scripts/atlas_motions.py then
moves each region between maps with its plate's rotation.
"""
import argparse
import io
import json
import sys
import zipfile
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from skimage import measure

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from measure_longitude_offsets import PackedModel  # noqa: E402
from rotation_model import rotate  # noqa: E402
from segment_landmass import (FIELD_SCALE, FIELD_WIDTH, FIELD_ZERO, PALETTE,  # noqa: E402
                              disc, hsv, thin_only)

CATALOGUE = ROOT / "sources/paleomap-atlas-2016.json"
GROUPS = ROOT / "annotations/paleomap-plate-groups.json"
OUT = ROOT / "data/derived/paleoatlas"
MODEL = "paleomap2016"

OCEAN_HUE = (170.0, 260.0)
OCEAN_BLUE_OVER_RED = 25.0   # shelf cyan and deep blue both clear this; grey-brown land does not
ICE_SATURATION = 0.12
ICE_VALUE = 0.55
INK_VALUE = 0.16             # black boundary lines
CREDIT_SATURATION = 0.6      # the small red credit in the lower left
LINE_RADIUS = 3              # widest overprinted stroke at 3600 px across
CLEAN_RADIUS = 3
MIN_AREA_PX = 300            # at 3600 x 1800, about 9 square degrees at the equator
MIN_THICKNESS_PX = 3.0       # pieces thinner than this are coastline slivers, not islands
NAME_MIN_FRACTION = 0.002    # a named region covers at least this share of the sphere (~1 Mkm2)
LABEL_SPACING_DEG = 12.0     # a shown name keeps this far from every larger shown name
MAX_PLATE_ID = 1000


def classify(rgb, continental):
    """Land booleans and the overprint that was refilled, for one full-size raster."""
    hue, saturation, value = hsv(rgb)
    blue = ((hue >= OCEAN_HUE[0]) & (hue <= OCEAN_HUE[1])
            & (rgb[..., 2] - rgb[..., 0] >= OCEAN_BLUE_OVER_RED))
    pale = (saturation <= ICE_SATURATION) & (value >= ICE_VALUE)
    red = (((hue <= 15.0) | (hue >= 340.0)) & (saturation >= CREDIT_SATURATION)
           & (value >= 0.5))
    overprint = thin_only(value <= INK_VALUE, LINE_RADIUS) | thin_only(red, LINE_RADIUS)
    if overprint.any():
        _, index = ndimage.distance_transform_edt(overprint, return_indices=True)
        blue, pale = blue[tuple(index)], pale[tuple(index)]
    land = (~blue & ~pale) | (pale & continental)
    return clean(land), overprint


def clean(land, radius=CLEAN_RADIUS):
    """Open then close, on a map that wraps in longitude.

    Morphology treats everything past the array edge as background, which erases the
    first and last few columns and so cuts every landmass that crosses the antimeridian
    in two. Padding with the other side of the map (and repeating the polar rows, which
    have no neighbour) keeps the seam and the poles as they are.
    """
    pad = 2 * radius
    padded = np.pad(np.pad(land, ((pad, pad), (0, 0)), mode="edge"),
                    ((0, 0), (pad, pad)), mode="wrap")
    padded = ndimage.binary_closing(ndimage.binary_opening(padded, disc(radius)), disc(radius))
    return padded[pad:-pad, pad:-pad]


def plate_groups():
    return json.loads(GROUPS.read_text())["groups"]


def group_lookup(groups):
    """Array from plate id to group index, -1 where no group claims the plate."""
    lookup = np.full(MAX_PLATE_ID, -1, dtype=np.int32)
    for index, group in enumerate(groups):
        claimed = set(group.get("plates", []))
        for low, high in group.get("ranges", []):
            claimed.update(range(low, high + 1))
        claimed -= set(group.get("except", []))
        for plate in claimed:
            if 0 <= plate < MAX_PLATE_ID and lookup[plate] < 0:
                lookup[plate] = index
    return lookup


def group_name(group, age):
    """The group's name at `age`, taking the oldest older name that applies."""
    name, name_en = group["name"], group["name_en"]
    for older in sorted(group.get("older_names", []), key=lambda entry: entry["from_ma"]):
        if age >= older["from_ma"]:
            name, name_en = older["name"], older["name_en"]
    return name, name_en


def plate_raster(model, age, width, height):
    """Plate id under each cell, from the rotated PALEOMAP polygons; 0 where there is none."""
    canvas = Image.new("I", (3 * width, height), 0)
    draw = ImageDraw.Draw(canvas)
    for feature in model.shapes:
        if not feature["to"] - 1e-9 <= age <= feature["from"] + 1e-9:
            continue
        turn = model.rotation(feature["pid"], age)
        if turn is None:
            continue
        for ring in feature["rings"]:
            points, last = [], None
            for index in range(0, len(ring), 2):
                longitude, latitude = rotate(turn, ring[index], ring[index + 1])
                if last is not None:
                    while longitude - last > 180:
                        longitude -= 360
                    while longitude - last < -180:
                        longitude += 360
                last = longitude
                points.append((longitude, latitude))
            if len(points) < 3:
                continue
            for shift in (-360, 0, 360):
                draw.polygon([((x + 180 + shift) / 360 * width + width,
                               (90 - y) / 180 * height) for x, y in points],
                             fill=int(feature["pid"]))
    return np.asarray(canvas, dtype=np.int32)[:, width:2 * width]


def continental_mask(model, age, width, height):
    """PALEOMAP continental polygons rotated to `age`, rasterised equirectangularly."""
    return plate_raster(model, age, width, height) > 0


def cell_weights(height, width):
    """Relative area of each equirectangular cell, proportional to cos(latitude)."""
    latitude = 90.0 - (np.arange(height) + 0.5) / height * 180.0
    return np.cos(np.radians(latitude))[:, None] * np.ones((1, width))


def wrapped_labels(land):
    """Connected pieces, joined across the antimeridian where they touch both edges."""
    labels, count = ndimage.label(land)
    if count == 0:
        return labels, 0
    parent = np.arange(count + 1)

    def find(value):
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    for left, right in zip(labels[:, 0], labels[:, -1]):
        if left and right:
            a, b = find(left), find(right)
            if a != b:
                parent[max(a, b)] = min(a, b)
    roots = np.array([find(value) for value in range(count + 1)])
    merged = roots[labels]
    unique = np.unique(merged[merged > 0])
    remap = np.zeros(count + 1, dtype=np.int32)
    remap[unique] = np.arange(1, len(unique) + 1)
    return remap[merged], len(unique)


def pixel_lonlat(col, row, width, height):
    return (-180.0 + (np.asarray(col) + 0.5) / width * 360.0,
            90.0 - (np.asarray(row) + 0.5) / height * 180.0)


def spherical_centroid(rows, cols, weights, width, height):
    """Area-weighted mean position on the sphere, safe across the antimeridian."""
    longitude, latitude = (np.radians(value) for value in pixel_lonlat(cols, rows, width, height))
    x = np.sum(weights * np.cos(latitude) * np.cos(longitude))
    y = np.sum(weights * np.cos(latitude) * np.sin(longitude))
    z = np.sum(weights * np.sin(latitude))
    return (float(np.degrees(np.arctan2(y, x))),
            float(np.degrees(np.arctan2(z, np.hypot(x, y)))))


def angular_distance(first, second):
    """Great-circle distance in degrees between two [lon, lat] points."""
    lon1, lat1, lon2, lat2 = (np.radians(value) for value in (*first, *second))
    cosine = (np.sin(lat1) * np.sin(lat2)
              + np.cos(lat1) * np.cos(lat2) * np.cos(lon2 - lon1))
    return float(np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0))))


def cap_radius(fraction):
    """Angular radius of a spherical cap covering `fraction` of the sphere."""
    return float(np.degrees(np.arccos(1.0 - 2.0 * min(0.5, fraction))))


def pieces_of(land, plates=None, age=0.0, groups=None):
    """Measured pieces with the keys the viewer already reads from the 2002 reports.

    With a plate raster, each piece is also split into plate-group regions and the
    largest region of each group is named.
    """
    height, width = land.shape
    weights = cell_weights(height, width)
    total = weights.sum()
    labels, count = wrapped_labels(land)
    # Distance to the nearest sea, tiled in longitude so a piece on the seam is not thin.
    tiled = np.tile(labels > 0, (1, 3))
    thickness = ndimage.distance_transform_edt(tiled)[:, width:2 * width]
    pieces = []
    keep = np.zeros(count + 1, dtype=bool)
    for label in range(1, count + 1):
        mask = labels == label
        area_px = int(mask.sum())
        if area_px < MIN_AREA_PX or thickness[mask].max() < MIN_THICKNESS_PX:
            continue
        keep[label] = True
        rows, cols = np.nonzero(mask)
        area = float(weights[mask].sum())
        centroid = spherical_centroid(rows, cols, weights[mask], width, height)
        inner = int(np.argmax(np.where(mask, thickness, -1)))
        inner_lon, inner_lat = pixel_lonlat(inner % width, inner // width, width, height)
        pieces.append({"label": label, "area_px": int(round(area)),
                       "area_fraction": round(area / total, 6),
                       "centroid": [round(centroid[0], 3), round(centroid[1], 3)],
                       "interior": [round(float(inner_lon), 3), round(float(inner_lat), 3)],
                       "radius_deg": round(cap_radius(area / total), 3),
                       "names": []})
    labels = np.where(keep[labels], labels, 0)
    pieces.sort(key=lambda piece: piece["area_px"], reverse=True)
    if plates is not None:
        describe_regions(labels, pieces, plates, weights, thickness, age,
                         groups if groups is not None else plate_groups())
    return labels, pieces


def region_interior(rows, cols):
    """The cell deepest inside a region, measured against the region's own edge.

    Measuring against the whole piece instead puts every region's label on its border
    nearest the piece's middle, so in a supercontinent the names crowd together.
    """
    top, left = rows.min(), cols.min()
    mask = np.zeros((rows.max() - top + 3, cols.max() - left + 3), dtype=bool)
    mask[rows - top + 1, cols - left + 1] = True
    depth = ndimage.distance_transform_edt(mask)
    row, col = np.unravel_index(int(np.argmax(depth)), depth.shape)
    return row + top - 1, col + left - 1


def describe_regions(labels, pieces, plates, weights, thickness, age, groups):
    """Split pieces by plate group, then name the largest region of each group."""
    height, width = labels.shape
    total = weights.sum()
    lookup = group_lookup(groups)
    slices = ndimage.find_objects(labels)
    largest = {}
    for piece in pieces:
        box = slices[piece["label"] - 1]
        inside = labels[box] == piece["label"]
        rows, cols = np.nonzero(inside)
        rows, cols = rows + box[0].start, cols + box[1].start
        plate_ids = np.clip(plates[rows, cols], 0, MAX_PLATE_ID - 1)
        group_ids = lookup[plate_ids]
        cell = weights[rows, cols]
        regions = []
        for group_index in np.unique(group_ids[group_ids >= 0]):
            chosen = group_ids == group_index
            area = float(cell[chosen].sum())
            plate = int(np.bincount(plate_ids[chosen], weights=cell[chosen]).argmax())
            centroid = spherical_centroid(rows[chosen], cols[chosen], cell[chosen], width, height)
            inner_row, inner_col = region_interior(rows[chosen], cols[chosen])
            inner_lon, inner_lat = pixel_lonlat(inner_col, inner_row, width, height)
            region = {"group": groups[group_index]["key"], "plate": plate,
                      "area_fraction": round(area / total, 6),
                      "centroid": [round(centroid[0], 3), round(centroid[1], 3)],
                      "interior": [round(float(inner_lon), 3), round(float(inner_lat), 3)],
                      "radius_deg": round(cap_radius(area / total), 3)}
            regions.append(region)
            key = region["group"]
            if key not in largest or area > largest[key][0]:
                largest[key] = (area, piece, region, groups[group_index])
        regions.sort(key=lambda region: region["area_fraction"], reverse=True)
        piece["regions"] = regions
    shown = []
    for area, piece, region, group in sorted(largest.values(), key=lambda entry: -entry[0]):
        if area / total < NAME_MIN_FRACTION or not group.get("label", True):
            continue
        # Largest first: a name that would sit on top of a bigger one stays in the report
        # for tracking but is not drawn, so central Asia does not turn into a pile of text.
        display = all(angular_distance(region["interior"], other) >= LABEL_SPACING_DEG
                      for other in shown)
        if display:
            shown.append(region["interior"])
        name, name_en = group_name(group, age)
        piece["names"].append({"name": name, "name_en": name_en,
                               "track": f"plate-group:{group['key']}",
                               "lon": region["interior"][0], "lat": region["interior"][1],
                               "display": display, "plate": region["plate"],
                               "area_fraction": region["area_fraction"],
                               "source": "PALEOMAP plate polygons"})


def signed_field(land, width=FIELD_WIDTH):
    """The same encoding as the 2002 fields: land positive, sea negative, around mid-grey."""
    small = np.asarray(Image.fromarray((land * 255).astype(np.uint8))
                       .resize((width, width // 2), Image.BILINEAR)) >= 128
    wide = np.tile(small, (1, 3))
    signed = (ndimage.distance_transform_edt(wide)
              - ndimage.distance_transform_edt(~wide))[:, width:2 * width]
    return np.clip(FIELD_ZERO + signed * FIELD_SCALE, 0, 255).astype(np.uint8), small


def outlines(labels, pieces, tolerance=1.5):
    """GeoJSON polygons in longitude and latitude, one feature per piece."""
    height, width = labels.shape
    features = []
    for rank, piece in enumerate(pieces):
        padded = np.pad((labels == piece["label"]).astype(np.uint8), 1)
        rings = []
        for contour in measure.find_contours(padded, 0.5):
            contour = measure.approximate_polygon(contour, tolerance)
            if len(contour) < 4:
                continue
            longitude, latitude = pixel_lonlat(contour[:, 1] - 1.5, contour[:, 0] - 1.5,
                                               width, height)
            ring = [[round(float(a), 3), round(float(b), 3)] for a, b in zip(longitude, latitude)]
            if ring[0] != ring[-1]:
                ring.append(ring[0])
            rings.append(ring)
        if rings:
            features.append({"type": "Feature",
                             "geometry": {"type": "Polygon", "coordinates": rings},
                             "properties": {"rank": rank + 1, "area_px": piece["area_px"],
                                            "centroid": piece["centroid"]}})
    return {"type": "FeatureCollection",
            "crs_note": "Equirectangular source; pixel centres map linearly to longitude "
                        "and latitude. Pieces crossing the antimeridian are one piece but "
                        "their outline is split at the seam.",
            "features": features}


def review(rgb, labels, pieces):
    out = (rgb * 0.45).astype(np.uint8)
    for rank, piece in enumerate(pieces):
        out[labels == piece["label"]] = PALETTE[rank % len(PALETTE)]
    return Image.fromarray(out).resize((1200, 600))


def segment(item):
    model = PackedModel(MODEL)
    with zipfile.ZipFile(ROOT / json.loads(CATALOGUE.read_text())["archive"]["path"]) as bundle:
        raw = bundle.read(item["member"])
    rgb = np.asarray(Image.open(io.BytesIO(raw)).convert("RGB")).astype(np.float32)
    height, width = rgb.shape[:2]
    plates = plate_raster(model, item["age_ma"], width, height)
    continental = plates > 0
    land, overprint = classify(rgb, continental)
    labels, pieces = pieces_of(land, plates, item["age_ma"])
    kept = labels > 0
    weights = cell_weights(height, width)
    field, small = signed_field(kept)

    stem = item["id"]
    OUT.mkdir(parents=True, exist_ok=True)
    Image.fromarray(field).save(OUT / f"{stem}-field.png")
    review(rgb, labels, pieces).save(OUT / f"{stem}-overlay.png")
    (OUT / f"{stem}-land.geojson").write_text(json.dumps(outlines(labels, pieces)))
    land_fraction = float(weights[kept].sum() / weights.sum())
    outside = float(weights[kept & ~continental].sum() / max(weights[kept].sum(), 1e-9))
    report = {
        "map_id": stem, "age_ma": item["age_ma"], "label": item["label"],
        "source": {"archive": json.loads(CATALOGUE.read_text())["archive"]["path"],
                   "member": item["member"], "sha256": item["sha256"]},
        "size_px": [width, height],
        "land_fraction": round(land_fraction, 4),
        "land_outside_plate_polygons": round(outside, 4),
        "overprint_px": int(overprint.sum()),
        "field": {"width": FIELD_WIDTH, "height": FIELD_WIDTH // 2, "scale": FIELD_SCALE,
                  "zero": FIELD_ZERO, "land_fraction": round(float(small.mean()), 4)},
        "settings": {"ocean_hue": OCEAN_HUE, "ocean_blue_over_red": OCEAN_BLUE_OVER_RED,
                     "ice": {"saturation_max": ICE_SATURATION, "value_min": ICE_VALUE,
                             "only_inside": f"{MODEL} continental polygons"},
                     "clean_radius": CLEAN_RADIUS, "min_area_px": MIN_AREA_PX,
                     "min_thickness_px": MIN_THICKNESS_PX},
        "names_note": ("The 2016 atlas carries no lettering. Names are the PALEOMAP plate "
                       "groups under each piece (annotations/paleomap-plate-groups.json); the "
                       "largest region of each group covering at least "
                       f"{NAME_MIN_FRACTION} of the sphere is named."),
        "pieces": pieces,
    }
    (OUT / f"{stem}-pieces.json").write_text(json.dumps(report, indent=1))
    return {"id": stem, "age": item["age_ma"], "land": report["land_fraction"],
            "outside": report["land_outside_plate_polygons"], "pieces": len(pieces),
            "names": sum(name["display"] for piece in pieces for name in piece["names"])}


def contact_sheet(rows):
    columns, cell_w, cell_h = 10, 300, 170
    sheet = Image.new("RGB", (columns * cell_w, cell_h * ((len(rows) + columns - 1) // columns)))
    draw = ImageDraw.Draw(sheet)
    for index, row in enumerate(rows):
        x, y = cell_w * (index % columns), cell_h * (index // columns)
        sheet.paste(Image.open(OUT / f"{row['id']}-overlay.png").resize((cell_w, 150)), (x, y))
        draw.text((x + 4, y + 152), f"{row['age']:g} Ma  land {row['land']:.2f}  "
                  f"n {row['pieces']}", fill=(255, 255, 255))
    sheet.save(OUT / "contact-sheet.png")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ids", nargs="*", help="map ids, e.g. paleoatlas-255; default all")
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()
    maps = json.loads(CATALOGUE.read_text())["maps"]
    chosen = [item for item in maps if not args.ids or item["id"] in args.ids]
    if args.ids and len(chosen) != len(args.ids):
        raise SystemExit("Unknown map id among: " + ", ".join(args.ids))
    with Pool(args.jobs) as pool:
        rows = pool.map(segment, chosen)
    rows.sort(key=lambda row: row["age"])
    if not args.ids:
        contact_sheet(rows)
    for row in rows:
        print(f"{row['id']:16} {row['age']:7.3f} Ma  land {row['land']:.3f}  "
              f"outside polygons {row['outside']:.3f}  pieces {row['pieces']}  "
              f"names {row['names']}")


if __name__ == "__main__":
    main()
