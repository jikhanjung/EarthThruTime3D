#!/usr/bin/env python3
"""Route the water over every PaleoDEM grid and write one river field per grid.

These fields estimate potential drainage from the reconstructed terrain under the
assumptions used here; they are not published ancient river reconstructions.
For each slice of the elevation series the 6-minute grid is resampled to the 2048 x 1024 texture, every pit is filled to
the level at which it spills, every land cell sends its water to the steepest of its
eight neighbours, and the area draining through each cell is summed. Rain is taken as
even and evaporation as nil, so the result is drained area, not discharge; sea level is
the grid's own 0 m; and every basin spills, since the grids are too smooth to tell a
basin closed by a gorge narrower than a cell (the Congo, Sichuan, the Pannonian plain)
from one closed for real (Chad, Tarim, Eyre). Salles et al. (2023) routed the same grids
the same way; their maps are the comparison, not a source, most being CC BY-NC-SA.

The texture, `<id>-rivers.png`, is RGB. Red is the river field: at each texel the
largest, over the river cells within CONE_RADIUS, of that cell's size less CONE_SLOPE
per texel of distance, where size is log10 of the drained area over CLASS_KM2 scaled
0..1. The page draws where the field passes a cut, so a line's width follows its river's
size, its edge is crisp at any zoom, and a mix of two grids' fields is a plausible
in-between, as the coastline's distance field is. A river cell drains at least
RIVER_KM2. Green is the lake: the depth of water pooled before it spills (the filled
surface less the routing surface), on a square-root scale that saturates at LAKE_M, so a
few metres already show. The plain fields carry none of it: their pits are the grid's
own closures, the gorge-closed Congo, Sichuan and Pannonian basins as much as Chad,
Tarim and Eyre, and painting them would show the every-basin-spills assumption as lakes
the size of countries. The ice slices carry only the pooling the ice and the crust's
deformation create: pools with at least half their footprint already pooling on the
bare grid are excluded. This overlap threshold is a display heuristic, not a validated
lake reconstruction. Blue is 0. Every field is RGB so the shader can read the green of any of
them; a one-channel PNG would decode grey and its rivers would read as lakes.

A grid whose sea-level slider reaches below its datum (the ice sidecar's `range_m`, written
by scripts/build_ice.py) is routed a second time with the sea at that lowest level, land
being everything above it, and the result written as `<id>-rivers-low.png`: the rivers of
the exposed shelf, which the page mixes in as the slider goes down. Pass --lows to write
only those.

The present grid is routed a third way, over the ice of the last glacial cycle, one field
per 2,500-year step of PaleoMIST 1.0 (Gowan et al. 2021, sources/paleomist.json): today's
ice is taken off the grid where the grid holds it (Greenland's surface; Antarctica is
already bed), the crust is pressed down by the step's glacial isostatic deformation, the
step's grounded ice is laid on top, the sea is set at the level the page gives that age,
and the water is routed over that surface, ice included, so meltwater runs off the sheets
along their margins and a lake dammed by ice fills to its spill and drains over it. Only
cells off the ice are drawn. The result is `<id>-rivers-ice-<years>.png`, named by the
step's age in years, with a sidecar `<id>-rivers-ice.json` listing each step's age, sea
level and whether it lowers the sea below every younger step's; the page mixes the two
steps bracketing its sea level. Pass --ice to write these.

The grids are interpretive surfaces. Their sampling interval is not a measure of
reconstruction accuracy; these lines are potential drainage paths, not known channels.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import netCDF4
import numpy as np
from PIL import Image
from scipy import ndimage
from skimage.morphology import reconstruction

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from scripts.build_paleodem import CATALOGUE, default_source, elevation, locate, resample  # noqa: E402
from build_ice import stack  # noqa: E402
import present_water  # noqa: E402

PALEOMIST = ROOT / "sources/paleomist.json"
ICE_STEP_KA = 2.5         # PaleoMIST's interval
DATED_KA = 25             # the ice sidecar holds the page's level per thousand years to here

EARTH_RADIUS_KM = 6371.0
RIVER_KM2 = 1e3           # the smallest drained area that makes a cell a river
CLASS_KM2 = (1e3, 1e7)    # size: log10 of the drained area over this span, 0..1
CONE_RADIUS = 4           # texels a river cell's cone reaches
CONE_SLOPE = 0.35         # size the cone loses per texel; a size-1 river is 2 texels wide either side at the 0.25 cut
LAKE_M = 250.0            # the pooled depth that saturates the green channel; square root below, so 2.5 m is 0.1
BURN_M = (50.0, 2000.0)   # the cut along today's rivers on the present grid: this deep for the smallest rank and
                          # for rank 1, linear in between, so a small river's trench never reaches a main stem's
                          # pool and two networks touching at a divide do not join
LAKE_FLOOR_M = 3.0        # a mapped lake shows at least this deep, so a shallow one (Chad, the Aral) is not lost to the cut
OFFSETS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def wrap(a):
    """The grid tiled three times in longitude, so a basin across the antimeridian fills as one."""
    return np.tile(a, (1, 3))


def unwrap(a):
    width = a.shape[1] // 3
    return a[:, width:2 * width]


def fill_sinks(z, land):
    """Every land cell raised to the lowest level from which it drains to the ocean."""
    zp = wrap(z)
    seed = np.where(wrap(land), zp.max() + 1.0, zp)
    return unwrap(reconstruction(seed, zp, method="erosion"))


def cell_geometry(shape):
    """Kilometres per row and per column of each row, and each cell's area in km2."""
    height, width = shape
    latitude = 90.0 - (np.arange(height) + 0.5) / height * 180.0
    dy = np.radians(180.0 / height) * EARTH_RADIUS_KM
    dx = np.radians(360.0 / width) * EARTH_RADIUS_KM * np.cos(np.radians(latitude))
    return dy, dx, np.repeat((dx * dy)[:, None], width, axis=1)


def shifted(a, dr, dc):
    """The array's value at (row + dr, column + dc), wrapping in longitude."""
    return np.roll(a, (-dr, -dc), axis=(0, 1))


def rows_ok(shape, dr):
    ok = np.ones(shape, bool)
    if dr < 0:
        ok[:min(-dr, shape[0])] = False
    if dr > 0:
        ok[max(0, shape[0] - dr):] = False
    return ok


def directions(surface, land):
    """Where each land cell's water goes: the flat index of the steepest of its eight
    neighbours, -1 in the ocean, where it stops. A filled lake is
    level, so its cells take the direction of a neighbour that already has one, in waves
    from the outlet inward; the wave number is returned so the accumulation can order them."""
    dy, dx, _ = cell_geometry(surface.shape)
    index = np.arange(surface.size).reshape(surface.shape)
    best = np.zeros_like(surface)
    down = np.full(surface.shape, -1, np.int64)
    for dr, dc in OFFSETS:
        distance = np.hypot(dr * dy, dc * dx)[:, None]
        gradient = (surface - shifted(surface, dr, dc)) / distance
        take = land & rows_ok(surface.shape, dr) & (gradient > best)
        best[take] = gradient[take]
        down[take] = shifted(index, dr, dc)[take]
    wave_of = np.zeros(surface.shape, np.int32)
    flat = land & (down < 0)
    wave = 0
    while flat.any():
        wave += 1
        resolved = ~flat
        before = flat.sum()
        for dr, dc in OFFSETS:
            take = flat & rows_ok(surface.shape, dr) & shifted(resolved, dr, dc) & (shifted(surface, dr, dc) == surface)
            down[take] = shifted(index, dr, dc)[take]
            wave_of[take] = wave
            flat[take] = False
        if flat.sum() == before:
            raise SystemExit("A level cell drains nowhere; the fill should not allow that")
    return down, wave_of


def drained_area(surface, land, down, wave_of):
    """The area in km2 draining through each cell, its own included: cells are visited from
    the highest down, and within a level lake from the outlet's far side inward."""
    _, _, area = cell_geometry(surface.shape)
    order = np.lexsort((-wave_of.ravel(), -surface.ravel()))
    order = order[land.ravel()[order]]
    total = area.ravel().tolist()
    downstream = down.ravel().tolist()
    for i in order.tolist():
        j = downstream[i]
        if j >= 0:
            total[j] += total[i]
    return np.asarray(total).reshape(surface.shape)


def river_field(drained, land, depth):
    """The texture: red each river cell's size spread as a cone over its neighbours, green
    the depth of water pooled before it spills on a square-root scale to LAKE_M, blue 0."""
    low, high = np.log10(CLASS_KM2)
    size = np.clip((np.log10(np.maximum(drained, 1.0)) - low) / (high - low), 0.0, 1.0)
    size = np.where(land & (drained >= RIVER_KM2), size, 0.0)
    field = np.zeros_like(size)
    for dr in range(-CONE_RADIUS, CONE_RADIUS + 1):
        for dc in range(-CONE_RADIUS, CONE_RADIUS + 1):
            reach = np.hypot(dr, dc)
            if reach <= CONE_RADIUS:
                # Longitude wraps; north and south edges are not neighbours.
                spread = shifted(size, dr, dc) - CONE_SLOPE * reach
                np.maximum(field, spread, out=field, where=rows_ok(size.shape, dr))
    lake = np.where(land, np.sqrt(np.clip(depth / LAKE_M, 0.0, 1.0)), 0.0)
    return np.round(np.dstack([field, lake, np.zeros_like(field)]) * 255).astype(np.uint8)


def lowest_levels(out):
    """Each grid's lowest slider level in metres, from the ice sidecar, where it is below 0."""
    path = out / "ice-sources.json"
    if not path.exists():
        return {}
    sheets = json.loads(path.read_text()).get("sheets", {})
    return {grid: sheet["range_m"][0] for grid, sheet in sheets.items() if sheet.get("range_m", [0])[0] < 0}


def paleomist_grid():
    manifest = json.loads(PALEOMIST.read_text())
    asset = manifest["assets"][0]
    return netCDF4.Dataset((ROOT / asset["path"]).parent / asset["unzip"] / manifest["grid"])


def paleomist_step(data, age_ka, width):
    """One PaleoMIST step on the texture grid, in metres: the bed, the grounded ice thickness
    and the crust's deformation, which is the SELEN sea-level change relative to the land
    less its mean over today's ocean, so the eustatic part, which the page's own level
    supplies, is left out and only the glacial isostatic part remains, positive where the
    crust is pressed down."""
    ages = -np.asarray(data.variables["time"][:]) / 1000.0
    index = int(np.argmin(np.abs(ages - age_ka)))
    if abs(ages[index] - age_ka) > 1e-6:
        raise SystemExit(f"PaleoMIST has no step at {age_ka} ka; its steps are every {ICE_STEP_KA} kyr to {ages.max():g}")
    latitude = np.asarray(data.variables["lat"][:])
    north_first = latitude[0] > 0
    field = lambda name, at: np.nan_to_num(np.asarray(data.variables[name][at], dtype=np.float64))  # noqa: E731
    on_texture = lambda z: resample(z if north_first else z[::-1], width)  # noqa: E731
    ocean = field("base_topography", ages.argmin()) < 0
    weights = np.cos(np.radians(latitude))[:, None] * ocean
    change = field("sea_level", index)
    eustatic = (change * weights).sum() / weights.sum()
    return (on_texture(field("base_topography", index)), np.maximum(on_texture(field("ice_thickness", index)), 0.0),
            on_texture(change - eustatic))


def ice_surface(z, base0, thickness0, thickness, deformation):
    """The routing surface at a step: the grid with today's ice taken off where the grid
    holds it (as much of the present thickness as the grid stands above the present bed),
    the crust pressed down by the deformation, and the step's ice on top."""
    return z - np.clip(z - base0, 0.0, thickness0) - deformation + thickness


def sea_at(surface, level, z):
    """The sea over a deformed surface: what the surface puts at or below the level and
    connects to the world ocean, across the antimeridian, plus whatever the grid itself
    held at or below the level (the Caspian and the other basins the grid keeps below its
    datum, sea as they always were). A depression the deformation opens inland is land: a
    lake that fills to its spill."""
    below = surface <= level
    labels, _ = ndimage.label(wrap(below))
    world = np.bincount(labels.ravel())[1:].argmax() + 1
    return below & (unwrap(labels == world) | (z <= level))


def step_levels(out, ages):
    """Each step's sea level, the page's own for that age: the ice sidecar's held level to
    DATED_KA, the stack's value beyond, a half step the mean of its two neighbours."""
    path = out / "ice-sources.json"
    if not path.exists():
        raise SystemExit(f"{path} is needed for the page's levels; run scripts/build_ice.py first")
    held = {low["age_ka"]: low["level_m"] for low in json.loads(path.read_text())["lows"]["paleodem-0000"]}
    levels = stack()
    at = lambda age: held[age] if age <= DATED_KA else levels[age]  # noqa: E731
    return {age: at(int(age)) if age == int(age) else (at(int(age)) + at(int(age) + 1)) / 2 for age in ages}


def today_outlets(today, land):
    """Where a river of today leaves the grid: every cell of its line that touches the sea.
    The routing takes the water out there, at the bottom of the river's cut, so each river
    drains down its own trench to its own mouth; a trench with no such cell would fill to
    the sea's level and join every other trench it touches at a divide, and the Amazon
    left through the Plata. A river ending inland keeps the routing's own rule: its basin
    fills and spills."""
    return (today["burn"] > 0.0) & ndimage.binary_dilation(~land, structure=np.ones((3, 3), bool)) & land


def today_lakes(today, land):
    """The green channel's share from HydroLAKES: each mapped lake at its mean depth, at
    least LAKE_FLOOR_M so the shallow ones still show, on land only."""
    if today is None:
        return np.zeros(land.shape)
    mapped = today["lakes"] > 0.0
    return np.where(land & mapped, np.maximum(today["lakes"], LAKE_FLOOR_M), 0.0)


def ice_slices(out, directory, catalogue, width, oldest):
    """The present grid routed over PaleoMIST's ice, one field per step to `oldest` ka."""
    item = next(item for item in catalogue["maps"] if item["age_ma"] == 0)
    z = resample(elevation(locate(directory, item)), width)
    today = present_water.load(out, z)
    data = paleomist_grid()
    base0, thickness0, _ = paleomist_step(data, 0.0, width)
    ages = [ICE_STEP_KA * k for k in range(1, int(round(oldest / ICE_STEP_KA)) + 1)]
    levels = step_levels(out, ages)
    for stale in out.glob(f"{item['id']}-rivers-ice-*.png"):
        stale.unlink()
    slices, lowest = [], 0.0
    for age in ages:
        started = time.time()
        _, thickness, deformation = paleomist_step(data, age, width)
        surface = ice_surface(z, base0, thickness0, thickness, deformation)
        ice, level = thickness > 0, levels[age]
        land = ~sea_at(surface, level, z)
        # Today's rivers and sinks only where there is no ice; the sheet's own surface drains.
        bare = None if today is None else {"burn": np.where(ice, 0.0, today["burn"]), "lakes": today["lakes"], "closed": today["closed"] & ~ice}
        drained, depth = route(surface, land, bare)
        lakes = np.maximum(ice_lakes(depth, z, level, today), today_lakes(today, land & ~ice))
        Image.fromarray(river_field(drained, land & ~ice, lakes), "RGB").save(
            out / f"{item['id']}-rivers-ice-{int(round(age * 1000))}.png")
        slices.append({"age_ka": age, "level_m": level, "lowers": level < lowest})
        lowest = min(lowest, level)
        print(f"{item['id']}  {age:4g} ka  sea {level:+.0f} m  ice {ice.mean():.1%} of the map  largest basin "
              f"{drained[land].max() / 1e6:.2f} Mkm2  {time.time() - started:.0f}s")
    (out / f"{item['id']}-rivers-ice.json").write_text(json.dumps({
        "method": ("The present grid routed over the ice of PaleoMIST 1.0 (Gowan et al. 2021) at each step: "
                   "today's ice taken off the grid where it holds it, the crust pressed down by the step's "
                   "glacial isostatic deformation, the step's grounded ice laid on top, the sea at the level "
                   "the page gives that age (the ice sidecar's held level to 25 ka, the Spratt & Lisiecki "
                   "stack beyond, half steps the mean of their neighbours), and only cells off the ice drawn. "
                   "`lowers` marks a step whose level is below every younger step's, the ones the page can "
                   "bracket by level."),
        "source": "https://doi.org/10.1594/PANGAEA.905800", "slices": slices}, indent=1))


def ice_lakes(depth, z, level, today=None):
    """The lakes the ice makes: each pool of a slice kept whole, or dropped whole, by whether
    the bare grid pools over the same ground at the same sea level. A basin the grid closes
    on its own (Tarim, the Congo, the Pannonian plain) pools in both, so it is no lake here
    any more than in the plain field, however the deformation tilts it; one the ice dams or
    the crust's deformation opens (Agassiz, the Baltic Ice Lake) pools only here. Subtracting
    depths instead leaves the tilt as a lake wherever the deformation varies across a closed
    basin. The bare grid is routed as the present field is, along today's rivers."""
    land = z > level
    bare = route(z, land, today)[1] > 0.0
    pools, count = ndimage.label(depth > 0.0)
    # Heuristic: a pool is the grid's own when the bare grid pools over half of it or more;
    # a finer rule would compare each pool's spill level in the two surfaces.
    own = ndimage.mean(bare, pools, np.arange(1, count + 1)) >= 0.5 if count else np.zeros(0, bool)
    return np.where(np.concatenate([[False], own])[pools], 0.0, depth)


def route(z, land, today=None):
    """The area in km2 draining through each cell of a grid at the texture's resolution, and
    the depth in metres of the water pooled in each cell before it spills (the fill). On
    the present grid `today` holds the present-water rasters: the routing surface is cut
    down along today's rivers, BURN_M deep by size, so the water follows them through the
    gorges the grid closes (the Danube at the Iron Gates), and each river leaves the grid
    where its line meets the sea. A basin closed today still fills and spills: which
    rivers end in a sink is not in the data used here. The pooled depth is measured against the grid
    itself, so the cut is never a lake."""
    if today is not None:
        land = land & ~today_outlets(today, land) & ~today["closed"]
        cut = np.where(today["burn"] > 0.0, BURN_M[0] + (BURN_M[1] - BURN_M[0]) * today["burn"], 0.0)
        surface = fill_sinks(z - cut, land)
    else:
        surface = fill_sinks(z, land)
    down, wave_of = directions(surface, land)
    return drained_area(surface, land, down, wave_of), np.maximum(surface - z, 0.0)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default=ROOT / "data/derived/paleodem", type=Path)
    parser.add_argument("--source", type=Path, help="directory of grids; default the 6-minute set when fetched")
    parser.add_argument("--width", type=int, default=2048, choices=(1024, 2048, 4096),
                        help="texture width; the served fields are 2048")
    parser.add_argument("--lows", action="store_true", help="write only the lowstand fields")
    parser.add_argument("--ice", action="store_true",
                        help="write only the present grid's fields routed over PaleoMIST's ice, one per 2,500-year step")
    parser.add_argument("--ice-to", type=float, default=float(DATED_KA), metavar="KA",
                        help="the oldest step --ice writes; PaleoMIST reaches 80 (default %(default)s)")
    parser.add_argument("ids", nargs="*", help="slice ids to build; default all")
    args = parser.parse_args()
    catalogue = json.loads(CATALOGUE.read_text())
    directory = args.source or default_source(catalogue)
    args.out.mkdir(parents=True, exist_ok=True)
    if args.ice:
        ice_slices(args.out, directory, catalogue, args.width, args.ice_to)
        return
    lows = lowest_levels(args.out)
    for item in catalogue["maps"]:
        if args.ids and item["id"] not in args.ids:
            continue
        if args.lows and item["id"] not in lows:
            continue
        started = time.time()
        z = resample(elevation(locate(directory, item)), args.width)
        today = present_water.load(args.out, z) if item["age_ma"] == 0 else None
        levels = [] if args.lows else [(0.0, "rivers")]
        if item["id"] in lows:
            levels.append((lows[item["id"]], "rivers-low"))
        for level, suffix in levels:
            land = z > level
            drained, _ = route(z, land, today)   # the grid's own pits are not lakes; today's mapped lakes are
            Image.fromarray(river_field(drained, land, today_lakes(today, land)), "RGB").save(args.out / f"{item['id']}-{suffix}.png")
            largest = drained[land].max() / 1e6 if land.any() else 0.0
            print(f"{item['id']}  {item['age_ma']} Ma  sea {level:+.0f} m  largest basin {largest:.2f} Mkm2  "
                  f"river cells {(land & (drained >= RIVER_KM2)).sum() / max(land.sum(), 1):.1%} of land  {time.time() - started:.0f}s")


if __name__ == "__main__":
    main()
