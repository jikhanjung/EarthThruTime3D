#!/usr/bin/env python3
"""Route the water over every PaleoDEM grid and write one river field per grid.

Nobody has mapped the rivers of 300 million years ago; what a grid can give is where
water would have had to run over the land it draws. For each slice of the elevation
series the 6-minute grid is resampled to the 2048 x 1024 texture, every pit is filled to
the level at which it spills, every land cell sends its water to the steepest of its
eight neighbours, and the area draining through each cell is summed. Rain is taken as
even and evaporation as nil, so the result is drained area, not discharge; sea level is
the grid's own 0 m; and every basin spills, since the grids are too smooth to tell a
basin closed by a gorge narrower than a cell (the Congo, Sichuan, the Pannonian plain)
from one closed for real (Chad, Tarim, Eyre). Salles et al. (2023) routed the same grids
the same way; their maps are the comparison, not a source, most being CC BY-NC-SA.

The texture, `<id>-rivers.png`, is one channel: at each texel the largest, over the
river cells within CONE_RADIUS, of that cell's size less CONE_SLOPE per texel of
distance, where size is log10 of the drained area over CLASS_KM2 scaled 0..1. The page
draws where the field passes a cut, so a line's width follows its river's size, its edge
is crisp at any zoom, and a mix of two grids' fields is a plausible in-between, as the
coastline's distance field is. A river cell drains at least RIVER_KM2.

The grids are smooth interpretive surfaces, so the lines show where trunk rivers must
have run, not real channels.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage
from skimage.morphology import reconstruction

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_paleodem import CATALOGUE, default_source, elevation, locate, resample  # noqa: E402

EARTH_RADIUS_KM = 6371.0
RIVER_KM2 = 1e3           # the smallest drained area that makes a cell a river
CLASS_KM2 = (1e3, 1e7)    # size: log10 of the drained area over this span, 0..1
CONE_RADIUS = 4           # texels a river cell's cone reaches
CONE_SLOPE = 0.35         # size the cone loses per texel; a size-1 river is 2 texels wide either side at the 0.25 cut
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
        ok[0] = False
    if dr > 0:
        ok[-1] = False
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


def river_field(drained, land):
    """The texture: each river cell's size, spread as a cone over its neighbours."""
    low, high = np.log10(CLASS_KM2)
    size = np.clip((np.log10(np.maximum(drained, 1.0)) - low) / (high - low), 0.0, 1.0)
    size = np.where(land & (drained >= RIVER_KM2), size, 0.0)
    field = np.zeros_like(size)
    for dr in range(-CONE_RADIUS, CONE_RADIUS + 1):
        for dc in range(-CONE_RADIUS, CONE_RADIUS + 1):
            reach = np.hypot(dr, dc)
            if reach <= CONE_RADIUS:
                np.maximum(field, shifted(size, dr, dc) - CONE_SLOPE * reach, out=field)   # np.roll wraps in longitude
    return np.round(field * 255).astype(np.uint8)


def route(z, land):
    """The area in km2 draining through each cell of a grid at the texture's resolution."""
    surface = fill_sinks(z, land)
    down, wave_of = directions(surface, land)
    return drained_area(surface, land, down, wave_of)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default=ROOT / "data/derived/paleodem", type=Path)
    parser.add_argument("--source", type=Path, help="directory of grids; default the 6-minute set when fetched")
    parser.add_argument("--width", type=int, default=2048, choices=(1024, 2048, 4096),
                        help="texture width; the served fields are 2048")
    parser.add_argument("ids", nargs="*", help="slice ids to build; default all")
    args = parser.parse_args()
    catalogue = json.loads(CATALOGUE.read_text())
    directory = args.source or default_source(catalogue)
    args.out.mkdir(parents=True, exist_ok=True)
    for item in catalogue["maps"]:
        if args.ids and item["id"] not in args.ids:
            continue
        started = time.time()
        z = resample(elevation(locate(directory, item)), args.width)
        land = z > 0
        drained = route(z, land)
        Image.fromarray(river_field(drained, land), "L").save(args.out / f"{item['id']}-rivers.png")
        largest = drained[land].max() / 1e6 if land.any() else 0.0
        print(f"{item['id']}  {item['age_ma']} Ma  largest basin {largest:.2f} Mkm2  "
              f"river cells {(land & (drained >= RIVER_KM2)).sum() / max(land.sum(), 1):.1%} of land  {time.time() - started:.0f}s")


if __name__ == "__main__":
    main()
