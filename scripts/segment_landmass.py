"""Separate landmasses from ocean in a Scotese map and label connected pieces.

This is an image-space segmentation of a published map, not a plate reconstruction.
Annotation drawn on top of the map (labels, subduction lines, the equator rule) is
masked out and refilled from its surroundings, so continent edges near a label are
interpolated, not observed.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage
from skimage import measure

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))
from core.globe import BOUNDS  # noqa: E402

# Hue/saturation gates measured from the map palette (see devlog).
OCEAN_HUE = (185.0, 260.0)
OCEAN_SATURATION = 0.25
OCEAN_BLUE_MARGIN = 25.0   # dark rainforest greens reach a blue-ish hue but stay near-grey in B-G
GLARE_HUE = (150.0, 265.0) # the painted sheen on open water runs cyan to blue
INK_VALUE = 0.20          # black equator rule and frame
LABEL_SATURATION = 0.18   # white lettering
LABEL_VALUE = 0.80
ANNOTATION_HUE = (5.0, 50.0)   # orange subduction zones and spreading ridges
ANNOTATION_SATURATION = 0.45
ANNOTATION_RADIUS = 3        # widest annotation stroke; ice sheets are far wider
ICE_VALUE = 0.86             # ice is painted pale: bright but washed out
ICE_SATURATION = 0.62        # open water stays strongly saturated even where it is bright
ICE_TEXTURE = 10.0           # ice is stippled; the ocean's bright glare is a smooth gradient
ICE_WINDOW = 5               # window for the local contrast measure
ICE_SEED_RADIUS = 2          # a seed this wide keeps lettering out of the ice mask
ICE_CLOSE_RADIUS = 6         # bridges the gaps lettering punches through an ice sheet

# Pale blue-white ice and the glare painted on open water share a colour and a
# texture, so the ice pass is not safe to run over a whole map. It is limited to the
# southern polar band and to maps where a pale southern landmass was confirmed by
# eye. Both the band and the map list are operator decisions, not source statements;
# maps outside the list get no ice pass, which is why their far south stays ocean.
ICE_SOUTH_OF = -58.0
POLAR_ICE_MAPS = {"000", "lgm", "014", "050"}

# The JPEG's black frame leaves a bright halo just inside the disc edge, which
# reads as ice. Trimming the rim costs a few pixels of coastline at the seam.
ELLIPSE_INSET_PX = 3


def hsv(rgb):
    r, g, b = (rgb[..., i] / 255.0 for i in range(3))
    high = np.maximum(np.maximum(r, g), b)
    low = np.minimum(np.minimum(r, g), b)
    span = np.maximum(high - low, 1e-6)
    hue = np.where(high == r, ((g - b) / span) % 6,
                   np.where(high == g, (b - r) / span + 2, (r - g) / span + 4)) * 60.0
    hue = np.where(high - low > 1e-6, hue, 0.0)
    return hue, np.where(high > 0, (high - low) / np.maximum(high, 1e-6), 0.0), high


def disc(radius):
    grid = np.mgrid[-radius:radius + 1, -radius:radius + 1]
    return np.hypot(*grid) <= radius


def ellipse_mask(shape, bounds):
    left, top, right, bottom = bounds
    rows, cols = np.mgrid[0:shape[0], 0:shape[1]]
    x = (cols - (left + right) / 2) / ((right - left) / 2)
    y = (rows - (top + bottom) / 2) / ((bottom - top) / 2)
    inside = x * x + y * y <= 1.0
    return ndimage.binary_erosion(inside, disc(ELLIPSE_INSET_PX))


def labels_for(map_id):
    path = BASE_DIR / "annotations/landmass-labels.json"
    if not path.exists():
        return []
    return json.loads(path.read_text())["maps"].get(map_id, [])


def forward_mollweide(longitude, latitude, bounds):
    """(longitude, latitude) in degrees -> pixel, matching projection.js."""
    longitude, latitude = np.radians(longitude), np.radians(latitude)
    theta = np.arcsin(np.clip(latitude / (np.pi / 2), -1.0, 1.0))
    for _ in range(60):
        theta -= ((2 * theta + np.sin(2 * theta) - np.pi * np.sin(latitude))
                  / (2 + 2 * np.cos(2 * theta)))
    left, top, right, bottom = bounds
    x = longitude / np.pi * np.cos(theta)
    return ((left + right) / 2 + x * (right - left) * 0.495,
            (top + bottom) / 2 - np.sin(theta) * (bottom - top) * 0.495)


def interior_point(mask):
    """The pixel furthest from the piece's edge, so a label never lands offshore."""
    distance = ndimage.distance_transform_edt(np.pad(mask, 1))[1:-1, 1:-1]
    row, col = np.unravel_index(int(np.argmax(distance)), distance.shape)
    return float(col), float(row)


def name_pieces(labels_map, pieces, anchors, bounds, tolerance_px=40.0):
    """Attach names to pieces by which piece each anchor falls in.

    An anchor that lands just offshore, which happens where cleanup trimmed a coast,
    is pulled to the nearest piece within `tolerance_px`; anything further is reported
    rather than guessed at.
    """
    by_label = {piece["label"]: piece for piece in pieces}
    for piece in pieces:
        piece["names"] = []
    unmatched = []
    for anchor in anchors:
        # An anchor is either a point read straight off the printed map (x, y in source
        # pixels, which is how the map's own labels were transcribed) or a geographic
        # position. Pixel anchors keep the name tied to what the map actually prints.
        if "x" in anchor:
            col, row = float(anchor["x"]), float(anchor["y"])
        else:
            col, row = forward_mollweide(anchor["lon"], anchor["lat"], bounds)
        column = int(round(col))
        line = int(round(row))
        label = 0
        if 0 <= line < labels_map.shape[0] and 0 <= column < labels_map.shape[1]:
            label = int(labels_map[line, column])
        if label == 0:
            distance, index = ndimage.distance_transform_edt(
                labels_map == 0, return_indices=True)
            if (0 <= line < labels_map.shape[0] and 0 <= column < labels_map.shape[1]
                    and distance[line, column] <= tolerance_px):
                label = int(labels_map[index[0][line, column], index[1][line, column]])
        if label == 0 or label not in by_label:
            unmatched.append(anchor["name"])
            continue
        longitude, latitude = inverse_mollweide(col, row, bounds)
        by_label[label]["names"].append(
            {"name": anchor["name"], "name_en": anchor.get("name_en"),
             "track": anchor.get("track"),
             "lon": round(float(longitude), 3), "lat": round(float(latitude), 3),
             "display": bool(anchor.get("display", True)),
             "source": "map label" if "x" in anchor else "position"})
    for piece in pieces:
        if len(piece["names"]) == 1:
            col, row = interior_point(labels_map == piece["label"])
            longitude, latitude = inverse_mollweide(col, row, bounds)
            piece["names"][0]["lon"] = round(float(longitude), 3)
            piece["names"][0]["lat"] = round(float(latitude), 3)
    return unmatched


def catalogue_maps():
    text = (BASE_DIR / "sources/scotese-earth-history.json").read_text()
    return json.loads(text)["maps"]


def thin_only(mask, radius=ANNOTATION_RADIUS):
    """Keep the drawn-on parts of a mask and release wide blobs.

    Lettering and the subduction lines are a few pixels across, while an ice sheet
    is hundreds. Anything that survives an opening is map content, not annotation.
    """
    wide = ndimage.binary_opening(mask, disc(radius))
    wide = ndimage.binary_dilation(wide, disc(radius))
    return mask & ~wide


def local_contrast(rgb, window=ICE_WINDOW):
    grey = rgb.mean(axis=2)
    mean = ndimage.uniform_filter(grey, window)
    mean_square = ndimage.uniform_filter(grey * grey, window)
    return np.sqrt(np.maximum(mean_square - mean * mean, 0.0))


def classify(rgb, inside, bounds, ice_south_of=ICE_SOUTH_OF, polar_ice=False):
    """Return land/ocean booleans plus the annotation mask that was refilled."""
    hue, saturation, value = hsv(rgb)
    texture = local_contrast(rgb)
    ocean = ((hue >= OCEAN_HUE[0]) & (hue <= OCEAN_HUE[1]) & (saturation >= OCEAN_SATURATION)
             & (rgb[..., 2] - rgb[..., 1] >= OCEAN_BLUE_MARGIN))
    # Some maps paint a bright cyan-white sheen on open water. It shares its colour
    # with ice, so it is told apart the same way: the sheen is smooth, ice is stippled.
    ocean |= ((hue >= GLARE_HUE[0]) & (hue <= GLARE_HUE[1]) & (value >= ICE_VALUE)
              & (saturation <= ICE_SATURATION) & (texture < ICE_TEXTURE))
    pale = (saturation <= LABEL_SATURATION) & (value >= LABEL_VALUE) & inside
    ink = (value <= INK_VALUE) & inside
    drawn = ((hue >= ANNOTATION_HUE[0]) & (hue <= ANNOTATION_HUE[1])
             & (saturation >= ANNOTATION_SATURATION) & (value >= 0.55) & inside)
    annotation = thin_only(pale) | thin_only(ink) | thin_only(drawn)
    # Ice sheets read as pale blue-white, and so does the glare painted on the open
    # ocean. Local contrast separates them: ice is stippled, the glare is smooth.
    if polar_ice:
        rows, cols = np.mgrid[0:inside.shape[0], 0:inside.shape[1]]
        polar = inverse_mollweide(cols, rows, bounds)[1] <= ice_south_of
    else:
        polar = np.zeros_like(inside)
    ice = (inside & polar & (value >= ICE_VALUE) & (saturation <= ICE_SATURATION)
           & (texture >= ICE_TEXTURE) & ~annotation)
    ice = ndimage.binary_closing(ice, disc(ICE_CLOSE_RADIUS)) & inside & polar
    # Refill annotation pixels from the nearest pixel that carries map colour.
    known = inside & ~annotation
    if annotation.any() and known.any():
        _, index = ndimage.distance_transform_edt(~known, return_indices=True)
        ocean = ocean[tuple(index)]
    land = (inside & ~ocean) | ice
    return land, inside & ~land, annotation


def clean(land, inside, open_radius, min_area):
    element = disc(open_radius)
    land = ndimage.binary_opening(land, element) & inside
    land = ndimage.binary_closing(land, element) & inside
    labels, count = ndimage.label(land)
    if count:
        areas = ndimage.sum_labels(land, labels, range(1, count + 1))
        keep = np.isin(labels, 1 + np.flatnonzero(areas >= min_area))
        land &= keep
    # Drop ocean specks fully enclosed by land only if they are tiny.
    holes, hole_count = ndimage.label(~land & inside)
    if hole_count:
        areas = ndimage.sum_labels(~land & inside, holes, range(1, hole_count + 1))
        fill = np.isin(holes, 1 + np.flatnonzero(areas < min_area))
        land |= fill
    return land


def components(land, min_area):
    labels, count = ndimage.label(land)
    pieces = []
    for index in range(1, count + 1):
        mask = labels == index
        area = int(mask.sum())
        if area < min_area:
            labels[mask] = 0
            continue
        rows, cols = np.nonzero(mask)
        pieces.append({"label": index, "area_px": area,
                       "centroid_px": [round(float(cols.mean()), 1), round(float(rows.mean()), 1)],
                       "bbox_px": [int(cols.min()), int(rows.min()), int(cols.max()), int(rows.max())]})
    pieces.sort(key=lambda piece: piece["area_px"], reverse=True)
    return labels, pieces


def inverse_mollweide(col, row, bounds):
    """Pixel centre -> (longitude, latitude) in degrees, mirroring projection.js."""
    left, top, right, bottom = bounds
    x = (col - (left + right) / 2) / ((right - left) * 0.495)
    y = ((top + bottom) / 2 - row) / ((bottom - top) * 0.495)
    theta = np.arcsin(np.clip(y, -1.0, 1.0))
    latitude = np.arcsin(np.clip((2 * theta + np.sin(2 * theta)) / np.pi, -1.0, 1.0))
    cos_theta = np.maximum(np.cos(theta), 1e-9)
    longitude = np.clip(np.pi * x / cos_theta, -np.pi, np.pi)
    return np.degrees(longitude), np.degrees(latitude)


def ring_area(ring):
    x = np.asarray([point[0] for point in ring])
    y = np.asarray([point[1] for point in ring])
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def rings(mask, bounds, tolerance):
    """Trace a piece into one or more lon/lat rings, outer ring first."""
    padded = np.pad(mask.astype(np.uint8), 1)
    traced = []
    for contour in measure.find_contours(padded, 0.5):
        contour = measure.approximate_polygon(contour, tolerance)
        if len(contour) < 4:
            continue
        rows = contour[:, 0] - 1
        cols = contour[:, 1] - 1
        longitude, latitude = inverse_mollweide(cols, rows, bounds)
        ring = [[round(float(a), 4), round(float(b), 4)] for a, b in zip(longitude, latitude)]
        if ring[0] != ring[-1]:
            ring.append(ring[0])
        traced.append(ring)
    traced.sort(key=lambda ring: abs(ring_area(ring)), reverse=True)
    return traced


def geojson(labels, pieces, bounds, map_id, age_ma, tolerance):
    features = []
    for rank, piece in enumerate(pieces):
        traced = rings(labels == piece["label"], bounds, tolerance)
        if not traced:
            continue
        features.append({
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": traced},
            "properties": {"map_id": map_id, "age_ma": age_ma, "rank": rank + 1,
                           "area_px": piece["area_px"], "names": piece.get("names", []),
                           "centroid_px": piece["centroid_px"]},
        })
    return {"type": "FeatureCollection",
            "crs_note": "Longitude/latitude derived by inverting an assumed Mollweide "
                        "projection of the source image; the true projection and central "
                        "meridian of the source map are unverified.",
            "features": features}


# Equirectangular signed-distance field, the form the viewer morphs between. Land is
# positive, ocean negative, encoded around mid-grey. Interpolating two of these and
# cutting at the midpoint moves a coastline instead of cross-fading two pictures.
FIELD_WIDTH = 1024
FIELD_SCALE = 2.0          # grey levels per pixel of distance
FIELD_ZERO = 128


def equirectangular(mask, bounds, width=FIELD_WIDTH):
    height = width // 2
    rows, cols = np.mgrid[0:height, 0:width]
    latitude = 90.0 - (rows + 0.5) / height * 180.0
    longitude = -180.0 + (cols + 0.5) / width * 360.0
    col, row = forward_mollweide(longitude, latitude, bounds)
    col = np.clip(np.round(col).astype(int), 0, mask.shape[1] - 1)
    row = np.clip(np.round(row).astype(int), 0, mask.shape[0] - 1)
    return mask[row, col]


def signed_field(mask, bounds, width=FIELD_WIDTH):
    land = equirectangular(mask, bounds, width)
    # Tile in longitude so the distance transform crosses the antimeridian instead of
    # treating it as an edge. Latitude has real edges at the poles and is left alone.
    wide = np.tile(land, (1, 3))
    inside = ndimage.distance_transform_edt(wide)
    outside = ndimage.distance_transform_edt(~wide)
    signed = (inside - outside)[:, width:2 * width]
    return np.clip(FIELD_ZERO + signed * FIELD_SCALE, 0, 255).astype(np.uint8), land


PALETTE = np.array([
    [230, 90, 70], [80, 190, 120], [250, 200, 60], [150, 120, 235], [245, 140, 60],
    [70, 200, 220], [235, 120, 190], [170, 210, 70], [120, 150, 250], [240, 170, 130],
    [110, 220, 180], [210, 110, 240], [200, 200, 200], [160, 110, 80], [90, 130, 90],
], dtype=np.uint8)


def overlay(rgb, labels, pieces):
    out = (rgb * 0.45).astype(np.uint8)
    for rank, piece in enumerate(pieces):
        colour = PALETTE[rank % len(PALETTE)]
        out[labels == piece["label"]] = colour
    edges = labels != ndimage.grey_erosion(labels, size=3)
    out[edges & (labels > 0)] = 255
    return Image.fromarray(out)


REVIEW_FONTS = ["/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
                "/usr/share/fonts/opentype/unifont/unifont.otf"]


def review_font(size=13):
    from PIL import ImageFont
    for path in REVIEW_FONTS:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def draw_names(image, pieces, bounds):
    from PIL import ImageDraw
    draw = ImageDraw.Draw(image)
    font = review_font()
    for piece in pieces:
        for name in piece.get("names", []):
            col, row = forward_mollweide(name["lon"], name["lat"], bounds)
            text = name["name"]
            box = draw.textbbox((col, row), text, font=font, anchor="mm")
            draw.rectangle([box[0] - 3, box[1] - 2, box[2] + 3, box[3] + 2], fill=(12, 20, 28))
            draw.text((col, row), text, font=font, fill=(255, 240, 200), anchor="mm")
    return image


def outline(rgb, labels, pieces):
    """Source image at full brightness with one coloured outline per piece."""
    out = rgb.astype(np.uint8).copy()
    border = (labels > 0) & (labels != ndimage.grey_erosion(labels, size=3))
    border |= (labels > 0) & ~ndimage.binary_erosion(labels > 0, disc(1))
    for rank, piece in enumerate(pieces):
        out[border & (labels == piece["label"])] = PALETTE[rank % len(PALETTE)]
    return Image.fromarray(out)


def locate(pieces, labels, bounds, disc_px):
    """Give each piece a position and an angular size on the globe.

    The centroid is where the piece sits; the interior point is where a label can go
    without landing offshore. The radius comes from the area, which is meaningful here
    because Mollweide is equal-area: a piece covering a fraction f of the disc covers
    the same fraction of the sphere, matching a cap of radius acos(1 - 2f).
    """
    for piece in pieces:
        column, row = piece["centroid_px"]
        longitude, latitude = inverse_mollweide(column, row, bounds)
        piece["centroid"] = [round(float(longitude), 3), round(float(latitude), 3)]
        column, row = interior_point(labels == piece["label"])
        longitude, latitude = inverse_mollweide(column, row, bounds)
        piece["interior"] = [round(float(longitude), 3), round(float(latitude), 3)]
        fraction = min(0.5, piece["area_px"] / max(disc_px, 1))
        piece["radius_deg"] = round(float(np.degrees(np.arccos(1.0 - 2.0 * fraction))), 3)
    return pieces


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("map_id", help="source image stem, e.g. 000 or LGM")
    parser.add_argument("--open-radius", type=int, default=2)
    parser.add_argument("--min-area", type=int, default=120)
    parser.add_argument("--polar-ice", action=argparse.BooleanOptionalAction, default=None,
                        help="run the southern ice pass (default: only reviewed maps)")
    parser.add_argument("--ice-south-of", type=float, default=ICE_SOUTH_OF,
                        help="latitude below which pale blue-white pixels count as ice")
    parser.add_argument("--simplify", type=float, default=0.8,
                        help="polygon simplification tolerance in source pixels")
    parser.add_argument("--out", default="data/derived/segmentation")
    args = parser.parse_args()

    source = BASE_DIR / "data/sources/scotese/images" / f"{args.map_id}.jpg"
    rgb = np.asarray(Image.open(source).convert("RGB")).astype(np.float32)
    bounds = BOUNDS[args.map_id.lower()]
    inside = ellipse_mask(rgb.shape[:2], bounds)

    polar_ice = (args.map_id.lower() in POLAR_ICE_MAPS if args.polar_ice is None
                 else args.polar_ice)
    land, ocean, annotation = classify(rgb, inside, bounds, args.ice_south_of, polar_ice)
    land = clean(land, inside, args.open_radius, args.min_area)
    labels, pieces = components(land, args.min_area)
    anchors = labels_for(args.map_id)
    unmatched = name_pieces(labels, pieces, anchors, bounds)
    locate(pieces, labels, bounds, int(inside.sum()))

    out_dir = BASE_DIR / args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    Image.fromarray((land * 255).astype(np.uint8)).save(out_dir / f"{args.map_id}-land.png")
    field, equirect = signed_field(land, bounds)
    Image.fromarray(field).save(out_dir / f"{args.map_id}-field.png")
    draw_names(overlay(rgb, labels, pieces), pieces, bounds).save(
        out_dir / f"{args.map_id}-overlay.png")
    outline(rgb, labels, pieces).save(out_dir / f"{args.map_id}-outline.png")
    age = next((item["age_ma"] for item in catalogue_maps()
                if item["id"].endswith(args.map_id.lower())), None)
    shapes = geojson(labels, pieces, bounds, args.map_id, age, args.simplify)
    (out_dir / f"{args.map_id}-land.geojson").write_text(json.dumps(shapes))

    report = {"map_id": args.map_id, "age_ma": age, "source": str(source.relative_to(BASE_DIR)),
              "bounds_px": bounds, "ellipse_px": int(inside.sum()),
              "land_px": int(land.sum()), "ocean_px": int(ocean.sum()),
              "annotation_px": int(annotation.sum()),
              "land_fraction": round(float(land.sum() / inside.sum()), 4),
              "field": {"width": FIELD_WIDTH, "height": FIELD_WIDTH // 2,
                        "scale": FIELD_SCALE, "zero": FIELD_ZERO,
                        "land_fraction": round(float(equirect.mean()), 4)},
              "settings": {"open_radius": args.open_radius, "min_area": args.min_area,
                           "ice_south_of": args.ice_south_of,
                           "polar_ice": polar_ice},
              "unmatched_names": unmatched, "pieces": pieces}
    (out_dir / f"{args.map_id}-pieces.json").write_text(json.dumps(report, indent=2))
    print(f"{args.map_id}: land {report['land_fraction']:.1%} of disc, "
          f"{len(pieces)} pieces, {len(shapes['features'])} polygons")
    for rank, piece in enumerate(pieces[:12]):
        named = " · ".join(name["name"] for name in piece["names"]) or "(이름 없음)"
        print(f"  {rank + 1:2d}. area {piece['area_px']:6d} px  {named}")
    if unmatched:
        print(f"  anchors with no piece: {', '.join(unmatched)}")


if __name__ == "__main__":
    main()
