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
smoothed by half a degree, wider along longitude toward the poles, so the atlas's
one-degree staircase rounds off and the edge does not break into spokes where the
texture's columns converge. Green stays empty, because the atlas draws one white for
sheet, shelf and sea ice alike. A grid whose map paints no ice gets no file, so the
overlay fades out across that gap, which there means retreat. The atlas prelude older
than 540 Ma gets none. Every mask has its enclosed gaps below HOLE_KM2 filled: the
atlas draws hachures, grey mountains and blue basins inside its white sheets and the
opening in segment_paleoatlas.clean turns the hachured white into holes, up to 5% of a
sheet; Natural Earth leaves nunataks and slivers between neighbouring polygons.

Where the atlas paints nothing but the land-ice volume of van der Meer et al. (2022) is
at least ICE_VOLUME_MKM3, the cut the sea-level strip already shades, the grid gets a
cap instead: everything poleward of the same paper's ice latitude for that age, both
hemispheres, the edge eased over two degrees. It is a modelled limit, not an outline,
and `ice-sources.json` beside the masks says for every grid whether its mask is
natural-earth, atlas or limit, so the page can say so too.

Red is not a mask but a signed distance to the ice edge, 128 at the edge and
ICE_FIELD_SCALE levels per degree, positive inside, so the shader can cut it at a level
other than the edge: the sea-level control moves the cut, and the ice grows or shrinks
with it. How far is decided on the page from a table written beside the masks: the
share of the globe inside each level of the field, and the paper's ice volume at that
age. A metre of sea level is 1/SEA_PER_MKM3 million km3 of ice (the paper's ratio), a
sheet's area goes as its volume to the AREA_EXPONENT, and the page cuts at the level
whose enclosed area matches, so the ice is gone at +2.5 m per million km3 of the
stop's ice and grows by the same law below. A uniform advance from the drawn edge is a
toy, real sheets grow from centres, so the present, the one stop with a dated
deglaciation, also gets one field per thousand years of it, `paleodem-0000-ice-low-<ka>.png`:
the optimal North American margins of NADI-1 (Dalton et al. 2023) and the most-credible
Eurasian margins of DATED-1 (Hughes et al. 2016) laid over today's ice, so Antarctica,
Greenland, Iceland and the mountain glaciers keep their present extent. Each slice
carries the sea level of its age from the Spratt & Lisiecki (2016) stack, taken as the
running minimum back from the present so the levels fall with age. Every thousand years
is written for the time window, which steps through the ages; a slice that lowers
nothing is marked so the sea-level what-if, which mixes the two slices bracketing the
offset, skips it. Older than the dated margins, 26 to MODEL_TO_KA, the slices come from
PaleoMIST 1.0 (Gowan et al. 2021, sources/paleomist.json, where fetched): its grounded
ice every 2,500 years, mixed between the two steps bracketing each thousand years, and
only where the dated margins ever reached, MODEL_REACH_DEGREES around the ice NADI-1 and
DATED-1 added over today's, so Antarctica, Patagonia and the mountain ranges keep their
present extent as they do in the dated slices and nothing appears at 26 ka that vanishes
at 25. Each carries the stack's own level for its age, not the running minimum, which the
window shows and the what-if does not use (`lowers` is false: none is below 24 ka's).
PaleoMIST is a minimal MIS 3 scenario whose own sea level sits well above the stack's
(jikhanjung 100); its ocean-mean level per step goes beside the slices as `model_levels`
so the page can draw the disagreement.

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
import math
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
from build_sealevel import pleistocene  # noqa: E402
import paleomist  # noqa: E402
from segment_paleoatlas import cell_weights, ice, plate_raster  # noqa: E402

MANIFEST = ROOT / "sources/ice.json"
SEALEVEL = ROOT / "sources/sealevel.json"
ANCHORS = ROOT / "sources/ice-anchors.json"
ICE_VOLUME_MKM3 = 5.0                        # the strip's cut: a fifth of today's land ice
ICE_FIELD_SCALE = 8.0                        # levels per degree in the red channel, 128 at the edge
SEA_PER_MKM3 = 2.5                           # metres of sea level per million km3 of ice, the paper's ratio
AREA_EXPONENT = 0.8                          # a sheet's area goes as its volume to this power
TABLE_STEP = 8                               # the area table samples the field every 8 levels
HOLE_KM2 = 500_000.0                         # an enclosed gap smaller than this inside a sheet is filled
EARTH_KM2 = 510.1e6
SLICES_KA = range(1, 26)                     # the deglacial slices offered, one per thousand years
MODEL_TO_KA = 80                             # the PaleoMIST slices, 26 ka to here, one per thousand years
MODEL_REACH_DEGREES = 3.0                    # how far past the dated margins' footprint the model's ice is kept
NADI = "nadi1/NADI-1 shapefiles Dalton et al. QSR/{age}ka_cal_OPTIMAL_NADI-1_Dalton_etal_QSR.shp"
DATED = "dated1/DATED1 TimeSlices shp/TS{age}_mc.shp"   # from 25 to 10 ka; Eurasia is ice-free after
WGS84_A, WGS84_E2 = 6378137.0, 2 / 298.257223563 - 1 / 298.257223563 ** 2
ICE_LAT_COLUMN, ICE_VOLUME_COLUMN = 13, 22   # IceLat_degrees AVG, VolLandice_km3 AVG in Supplementary Table 1
ATLAS = ROOT / "sources/paleomap-atlas-2016.json"
GRIDS = ROOT / "sources/paleodem-slices.json"
WIDTH, HEIGHT = 2048, 1024
NEAREST_MA = 5.0
NEAR_DEGREES = 5.0    # a deposit this close to the drawn edge counts as agreeing
DEPOSITS = ("PresentDay_LithData_Scotese2008_410-0Ma/"
            "PresentDay_GlacialDeposits_Scotese2008_410-0Ma.shp")


def rasterise(path, width=WIDTH, height=HEIGHT, transform=None):
    """Every polygon part of a shapefile filled, in longitude/latitude unless `transform`
    turns the file's coordinates into them first."""
    image = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(image)
    reader = shapefile.Reader(str(path))
    for shape in reader.iterShapes():
        points = np.asarray(shape.points, dtype=float)
        if transform is not None:
            points = transform(points)
        parts = list(shape.parts) + [len(points)]
        for start, end in zip(parts, parts[1:]):
            ring = [((lon + 180.0) / 360.0 * width, (90.0 - lat) / 180.0 * height)
                    for lon, lat in points[start:end]]
            if len(ring) >= 3:
                draw.polygon(ring, fill=255)
    return np.asarray(image)


def polar_laea_inverse(points):
    """North-polar Lambert azimuthal equal-area metres on WGS84 back to longitude and
    latitude, DATED-1's projection (Snyder 1987, eqs. 24-15 to 24-19 and 3-18)."""
    a, e2 = WGS84_A, WGS84_E2
    e = math.sqrt(e2)
    q_pole = (1 - e2) * (1 / (1 - e2) - math.log((1 - e) / (1 + e)) / (2 * e))
    x, y = points[:, 0], points[:, 1]
    longitude = np.degrees(np.arctan2(x, -y))
    beta = np.arcsin(np.clip((q_pole - (x * x + y * y) / (a * a)) / q_pole, -1.0, 1.0))
    latitude = (beta + (e2 / 3 + 31 * e2 ** 2 / 180 + 517 * e2 ** 3 / 5040) * np.sin(2 * beta)
                + (23 * e2 ** 2 / 360 + 251 * e2 ** 3 / 3780) * np.sin(4 * beta)
                + (761 * e2 ** 3 / 45360) * np.sin(6 * beta))
    return np.column_stack([longitude, np.degrees(latitude)])


def share(mask):
    """Share of the globe under a mask, in percent, cells weighted by area."""
    weights = cell_weights(*mask.shape)
    return float(weights[mask > 0].sum() / weights.sum()) * 100


def present(folders):
    grounded = rasterise(next(folders["glaciated"].glob("*.shp")))
    shelves = rasterise(next(folders["shelves"].glob("*.shp")))
    print(f"grounded ice {share(grounded):.2f}% of the globe, shelves {share(shelves):.2f}% -> paleodem-0000-ice.png")
    return grounded, shelves


def fill_holes(inside, cap_km2=HOLE_KM2):
    """Fill the enclosed gaps of a mask that are smaller than cap_km2.

    The map wraps in longitude, and each polar row is one point: a gap touching a fully
    iced polar row is enclosed, one touching an open polar row is not. No drawn sheet has
    a real ice-free enclave anywhere near the cap (the largest gap in any map was 480,000
    km2, in the atlas's last glacial maximum), while Hudson Bay, which a deglacial slice
    may hold as an enclave, is 1,200,000 km2 and stays.
    """
    height, width = inside.shape
    pole = lambda row: np.full((1, width), row.all())  # noqa: E731
    padded = np.pad(np.vstack([pole(inside[0]), inside, pole(inside[-1])]),
                    ((0, 0), (width // 2, width // 2)), mode="wrap")
    gaps = ndimage.binary_fill_holes(padded)[1:-1, width // 2:width // 2 + width] & ~inside
    labels, count = ndimage.label(gaps)
    if not count:
        return inside
    weights = cell_weights(height, width)
    sizes = ndimage.sum(weights, labels, range(1, count + 1)) / weights.sum() * EARTH_KM2
    small = np.concatenate([[False], sizes < cap_km2])
    return inside | small[labels]


def distance_field(red):
    """The soft mask, its gaps filled, as a signed distance to its edge, in degrees, encoded around 128."""
    inside = fill_holes(red >= 128)
    height, width = inside.shape
    degrees = 360.0 / width      # the grid is square in degrees, so one figure serves both axes
    signed = (ndimage.distance_transform_edt(inside) - ndimage.distance_transform_edt(~inside)) * degrees
    return np.clip(128.0 + signed * ICE_FIELD_SCALE, 0, 255).astype(np.uint8)


def sea_range(age, volume, intervals):
    """The slider's two ends at a stop, in metres: the glacial maximum from the anchors, a
    full swing where the grid sits at an interglacial and half elsewhere, and the stop's
    whole ice melted at SEA_PER_MKM3 per million km3, rounded out to 10 m."""
    if volume <= 0:
        return [0, 0]
    top = int(math.ceil(volume * SEA_PER_MKM3 / 10.0) * 10)
    bottom = 0
    for entry in intervals:
        if entry["to_ma"] <= age <= entry["from_ma"]:
            bottom = -int(round(entry["swing_m"] * (1.0 if entry.get("full") else 0.5) / 10.0) * 10)
            break
    return [bottom, top]


def area_table(field):
    """The share of the globe inside each sampled level of a distance field, level 0 to
    256 every TABLE_STEP; the page cuts where this matches the area the offset implies."""
    weights = cell_weights(*field.shape)
    total = weights.sum()
    return [round(float(weights[field >= level].sum() / total), 5) for level in range(0, 257, TABLE_STEP)]


def stack():
    """Spratt & Lisiecki (2016) per thousand years: age in ka -> metres above present."""
    manifest = json.loads(SEALEVEL.read_text())
    path = next(ROOT / asset["path"] for asset in manifest["assets"] if asset["path"].endswith("spratt2016-noaa.txt"))
    return {int(round(age)): level for age, level in pleistocene(path)}


def held_levels(levels, ages=SLICES_KA):
    """Each age's sea level as the running minimum back from the present, and whether it
    lies below every younger age's, as (age, level, lowers). The stack starts above
    today's level, which is its noise, so the present counts as 0 m."""
    held, lowest = [], 0.0
    for age in ages:
        lowers = levels[age] < lowest
        lowest = min(lowest, levels[age])
        held.append((age, lowest, lowers))
    return held


def deglacial(folders, grounded, levels, today, out):
    """The last deglaciation as dated lowstand fields over today's ice, one per thousand
    years: NADI-1's optimal North American margins and DATED-1's most-credible Eurasian
    margins, each at the running minimum of the stack's level back from the present.

    Every age is written, because the time window steps through them all; `lowers` marks
    the ones whose level is below every younger slice's, the only ones the sea-level
    what-if can mix between, since a level that does not fall has no single age."""
    for stale in out.glob("paleodem-0000-ice-low*.png"):
        stale.unlink()
    slices, added = [], np.zeros(grounded.shape, bool)
    for age, level, lowers in held_levels(levels):
        mask = grounded > 0
        mask |= rasterise(folders["nadi1"].parent / NADI.format(age=age)) > 0
        dated = folders["dated1"].parent / DATED.format(age=age)
        if dated.exists():
            mask |= rasterise(dated, transform=polar_laea_inverse) > 0
        added |= mask & ~(grounded > 0)
        field = distance_field(mask.astype(np.uint8) * 255)
        Image.fromarray(np.dstack([field, np.zeros_like(field), np.zeros_like(field)])).save(out / f"paleodem-0000-ice-low-{age}.png")
        slices.append({"age_ka": age, "level_m": level, "lowers": lowers,
                       "volume": today - level / SEA_PER_MKM3, "areas": area_table(field)})
        print(f"  {age:2d} ka  sea {level:7.1f} m{'' if lowers else ' (held)'}  ice {share(field >= 128):5.2f}% "
              f"of the globe -> paleodem-0000-ice-low-{age}.png")
    return slices, added


def model_footprint(added, width=WIDTH):
    """Where the model's ice is kept: within MODEL_REACH_DEGREES of any ice the dated margins
    added over today's, on the grid's own degree scale."""
    return ndimage.distance_transform_edt(~added) * (360.0 / width) <= MODEL_REACH_DEGREES


def model_fields(data, grounded, footprint, ages):
    """PaleoMIST's grounded ice at each step, over today's ice and inside the footprint, as
    a distance field: age -> field."""
    fields = {}
    for age in ages:
        thick = paleomist.on_texture(paleomist.field(data, "ice_thickness", paleomist.step(data, age)), WIDTH) > 0
        mask = (grounded > 0) | (thick & footprint)
        fields[age] = distance_field(mask.astype(np.uint8) * 255)
        print(f"  PaleoMIST {age:4g} ka  ice {share(thick):5.2f}% of the globe, {share(thick & ~footprint & ~(grounded > 0)):.2f}% "
              f"beyond today's ice and the dated margins' reach dropped")
    return fields


def model_levels(data):
    """PaleoMIST's own sea level per step, the mean of its `sea_level` change over today's
    ocean, oldest first: the curve the window draws beside the stack's."""
    latitude = np.asarray(data.variables["lat"][:])
    latitude = latitude if latitude[0] > 0 else latitude[::-1]
    steps = paleomist.ages(data)
    ocean = paleomist.field(data, "base_topography", steps.argmin()) < 0
    weights = np.cos(np.radians(latitude))[:, None] * ocean
    return [[float(age) + 0.0, round(float((paleomist.field(data, "sea_level", index) * weights).sum() / weights.sum()), 1)]
            for index, age in sorted(enumerate(steps), key=lambda pair: -pair[1])]


def modelled(grounded, added, levels, today, out, youngest=SLICES_KA[-1], oldest=MODEL_TO_KA, data=None):
    """The PaleoMIST slices, the age after `youngest` to `oldest`, one per thousand years,
    each mixed from the two steps bracketing its age (the step itself where the age is
    one). None, and a note, where the grid has not been fetched."""
    if data is None:
        if not paleomist.grid_path().exists():
            print(f"no PaleoMIST grid at {paleomist.grid_path()}; slices past {youngest} ka not written")
            return [], []
        data = paleomist.grid()
    step = paleomist.STEP_KA
    ages = sorted({step * k for k in range(int((youngest + 1) // step), int(oldest / step) + 1)})
    fields = model_fields(data, grounded, model_footprint(added), ages)
    slices = []
    for age in range(youngest + 1, oldest + 1):
        below, above = step * (age // step), step * (age // step + 1)
        if above > oldest and age != oldest:
            break
        if below == age:
            field = fields[below]
        else:
            t = (age - below) / step
            field = np.round(fields[below] * (1 - t) + fields[above] * t).astype(np.uint8)
        Image.fromarray(np.dstack([field, np.zeros_like(field), np.zeros_like(field)])).save(out / f"paleodem-0000-ice-low-{age}.png")
        slices.append({"age_ka": age, "level_m": levels[age], "lowers": False, "source": "paleomist",
                       "volume": today - levels[age] / SEA_PER_MKM3, "areas": area_table(field)})
        print(f"  {age:2d} ka  sea {levels[age]:7.1f} m (stack)  ice {share(field >= 128):5.2f}% "
              f"of the globe -> paleodem-0000-ice-low-{age}.png")
    return slices, model_levels(data)


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


def polar_smooth(mask, base_px=5.0, cap_px=80):
    """Blur the mask by half a degree, wider along longitude toward the poles, so its edge
    stays soft and round on the globe.

    The atlas's white is read from one-degree cells, so the mask's edge is a staircase, and
    every column of an equirectangular texture becomes a wedge at the pole, so that
    staircase turned into spokes when the globe was viewed from above Antarctica. A
    Gaussian of base_px along latitude and base_px / cos(latitude) along longitude,
    capped at cap_px (8 degrees of longitude), rounds the steps and averages the wedges
    into an edge the shader's smoothstep draws cleanly; the threshold afterwards keeps
    the shape where the columns are not squeezed.
    """
    height, width = mask.shape
    out = ndimage.gaussian_filter1d(mask.astype(np.float32), base_px, axis=0, mode="nearest")
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
    field = distance_field(grounded)
    Image.fromarray(np.dstack([field, shelves, np.zeros_like(field)])).save(args.out / "paleodem-0000-ice.png")
    today = reference[0][1]
    intervals = json.loads(ANCHORS.read_text())["intervals"]
    sheets = {"paleodem-0000": {"volume": today, "areas": area_table(field),
                                "range_m": sea_range(0.0, today, intervals)}}
    print("deglacial slices over today's ice, NADI-1 and DATED-1 at the stack's sea level:")
    levels = stack()
    dated, added = deglacial(folders, grounded, levels, today, args.out)
    print(f"PaleoMIST slices over today's ice, {SLICES_KA[-1] + 1} to {MODEL_TO_KA} ka at the stack's own level:")
    reconstructed, curve = modelled(grounded, added, levels, today, args.out)
    lows = {"paleodem-0000": dated + reconstructed}

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
            field = distance_field(red)
            Image.fromarray(np.dstack([field, np.zeros_like(field), np.zeros_like(field)])).save(target)
            volume = reference.get(int(round(item["age_ma"])), (None, 0.0))[1]
            sheets[item["id"]] = {"volume": volume, "areas": area_table(field),
                                  "range_m": sea_range(float(item["age_ma"]), volume, intervals)}
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
        "sheets_method": ("Per grid, the paper's land-ice volume in million km3 at that age and the share of "
                          f"the globe inside each level of the mask's distance field, level 0 to 256 every "
                          f"{TABLE_STEP}. The page turns the sea-level offset into a volume at 1/{SEA_PER_MKM3:g} "
                          f"million km3 per metre, an area as volume to the {AREA_EXPONENT:g}, and cuts the field "
                          "at the level enclosing that area."),
        "ranges_method": ("Each sheet's range_m is the sea-level slider's two ends at that stop: the glacial "
                          "maximum from sources/ice-anchors.json (a full swing at an interglacial, half a swing "
                          "elsewhere, nothing outside the anchored icehouses) and the stop's whole ice melted "
                          f"at {SEA_PER_MKM3:g} m per million km3."),
        "lows_method": ("Dated lowstands where a deglaciation is reconstructed: the present's is one field per "
                        "thousand years of the last deglaciation, `<id>-ice-low-<ka>.png`, NADI-1's optimal "
                        "North American margins and DATED-1's most-credible Eurasian margins over today's ice, "
                        "each at its age's sea level from the Spratt & Lisiecki stack taken as the running "
                        "minimum back from the present. The time window steps through every slice; the sea-level "
                        "what-if uses only those whose `lowers` is true, mixes the two bracketing the offset "
                        f"and applies the area law below the deepest. From {SLICES_KA[-1] + 1} to {MODEL_TO_KA} ka "
                        "(`source` paleomist) the slice is PaleoMIST 1.0's grounded ice mixed between the two "
                        "2,500-year steps bracketing the age, kept only within "
                        f"{MODEL_REACH_DEGREES:g} degrees of the ice the dated margins ever added over today's, "
                        "at the stack's own level for the age; a minimal MIS 3 scenario, whose own ocean-mean "
                        "sea level per step is `model_levels` [age_ka, level_m], oldest first."),
        "grids": sources, "sheets": sheets, "lows": lows, "model_levels": curve}, indent=1))
    print(f"{written} grids given the atlas's ice ({borrowed} borrowing a map at another age), "
          f"{capped} a cap at the paper's limit, {len(report)} maps read; "
          f"{len(points)} deposits in the check -> ice-check.json, ice-sources.json")
    for map_id, row in report.items():
        print(f"  {map_id} {row['age_ma']:6g} Ma  ice {row['ice_share']:5.2f}%  deposits {row['deposits']:3d}: "
              f"inside {row['inside']} near {row['near']} dropped {row['dropped']} "
              f"outside {row['outside']} unrotated {row['unrotated']}")


if __name__ == "__main__":
    main()
