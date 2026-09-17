#!/usr/bin/env python3
"""Today's rivers and lakes on the texture grid, for the present stop's routing.

The 20 km grid closes every gorge narrower than a cell, so routed on the grid alone the
Danube fills the Pannonian basin and leaves it north through the Moravian Gate. Where
the rivers of today are known they need not be guessed: Natural Earth's 10 m river
centrelines (public domain) give the courses of the world's rivers with a size rank,
and HydroLAKES (Messager et al. 2016, CC BY 4.0) every lake of 10 ha and more with its
mean depth. This module rasterises what the present grid's routing uses
(sources/present-water.json): the rivers as one-texel lines carrying a size from their
rank, along which scripts/build_rivers.py cuts the routing surface (the burn), and the
lakes of LAKE_KM2 or more with their mean depth, the green channel of the present
fields, those the grid holds at or below its datum marked so the routing lets the water
out of the grid there at every sea level. Only the present grid has this; the
older grids keep the routing's own assumptions. The rasters are cached beside the
fields as `paleodem-0000-present-water.npz`.

HydroRIVERS was tried first and dropped: its licence is WWF's HydroSHEDS agreement
(an end-user licence and a fixed attribution for derivative works), not CC BY like
HydroLAKES's own.
"""
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import shapefile
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

MANIFEST = ROOT / "sources/present-water.json"
LAKE_KM2 = 100.0     # a lake rasterised from this area; a texel is about 400 km2 at the equator
RIVER_KINDS = ("River", "River (Intermittent)", "Lake Centerline")   # not canals
EXTEND_CELLS = 20    # how far (texels, 400 km) a line ending short of the grid's sea is carried on to it
BRIDGE_CELLS = 3     # how far (texels, 60 km) a line ending short of the river it joins is carried on to it
RULES = 2            # the rasterisation rules' version, part of the cache key: bump it when they change


def readers(manifest):
    """A shapefile reader per source role, from inputs verified against the manifest: an
    archive that is kept is hashed and read directly, one discarded after extraction
    (HydroLAKES) is read from the folder the fetcher's receipt binds to it, its files
    hashed. FileNotFoundError or ValueError when a source is not fetched or differs."""
    from fetch_paleodem import verify, verify_extracted
    found = {}
    for asset in manifest["assets"]:
        archive = ROOT / asset["path"]
        if asset.get("discard"):
            folder = archive.parent / asset["unzip"]
            verify_extracted(folder, asset)
            found[asset["role"]] = shapefile.Reader(str(folder / asset["layer"]), encodingErrors="replace")
        else:
            verify(archive, asset)
            with zipfile.ZipFile(archive) as opened:
                parts = {ext: io.BytesIO(opened.read(f"{asset['layer']}.{ext}")) for ext in ("shp", "shx", "dbf")}
            found[asset["role"]] = shapefile.Reader(**parts, encodingErrors="replace")
    return found


def to_texel(lon, lat, width, height):
    return (lon + 180.0) / 360.0 * width, (90.0 - lat) / 180.0 * height


def rivers(reader, width, height, z):
    """The rivers as one-texel lines carrying a size, 1 for Natural Earth's rank 1 (the
    Amazon, Nile, Mississippi, Yangtze) down to 0 at rank 12, the larger river where two
    cross. Lake centrelines keep a river continuous through the lakes it flows through.

    Two corrections for the routing's sake. Where two rivers touch anywhere but at the
    lower end of one of them they pass each other across a divide (the Guaporé and the
    Paraguay at the Pantanal, the Red and the Minnesota at the Traverse Gap), so the
    smaller one is broken at the contact, or the two trenches would join and one basin
    drain through the other's mouth. And a feature whose lower end
    stops short of the grid's sea, at an estuary head the map draws as sea and the grid
    as land (the Amazon 250 km from its mouth), is carried on to the sea along the lowest
    path within EXTEND_CELLS, so its trench has an outlet."""
    features = []   # (size, line, river): the river is the name, or the record where it has none
    for number, (record, shape) in enumerate(zip(reader.iterRecords(fields=["scalerank", "featurecla", "name"]), reader.iterShapes())):
        if record["featurecla"] not in RIVER_KINDS:
            continue
        size = float(np.clip((12 - record["scalerank"]) / 11.0, 0.0, 1.0))
        parts = list(shape.parts) + [len(shape.points)]
        for start, end in zip(parts, parts[1:]):
            line = [to_texel(lon, lat, width, height) for lon, lat in shape.points[start:end]]
            if len(line) >= 2:
                features.append((size, line, record["name"] or f"#{number}", record["featurecla"]))
    cells = []                      # each feature's texels, in drawing order
    for size, line, *_ in features:
        image = Image.new("1", (width, height), 0)
        ImageDraw.Draw(image).line(line, fill=1, width=1)
        cells.append(np.argwhere(np.asarray(image, bool)))
    cover = {}
    for index, own in enumerate(cells):
        for r, c in own:
            cover.setdefault((r, c), set()).add(index)
    near = lambda r, c: {(r + dr, (c + dc) % width) for dr in (-1, 0, 1) for dc in (-1, 0, 1) if 0 <= r + dr < height}
    texel = lambda x, y: (min(int(y), height - 1), int(x) % width)
    # A feature's lower end is where it joins whatever it flows into; a contact there is a
    # junction. A contact at its upper end is a river starting at a divide (the Red River
    # at the Traverse Gap, where the Minnesota starts too), and a contact along the way a
    # divide passed by: both are broken, the smaller feature giving way.
    lower = []
    for _, line, *_ in features:
        a, b = texel(*line[0]), texel(*line[-1])
        lower.append({a, b} if z[a] == z[b] else {a} if z[a] < z[b] else {b})
    joins = [set().union(*(near(*e) for e in lower[i])) for i in range(len(features))]
    broken = 0
    for index, own in enumerate(cells):
        keep = np.ones(len(own), bool)
        for k, (r, c) in enumerate(own):
            others = set().union(*(cover.get(cell, set()) for cell in near(r, c))) - {index}
            for other in others:
                if features[other][2] == features[index][2]:
                    continue        # the same river: another part or its lake centreline
                if (r, c) in joins[index] or (r, c) in joins[other] or features[other][0] < features[index][0]:
                    continue        # a junction, or the other is the smaller: it breaks, not this one
                if features[other][0] == features[index][0] and other > index:
                    continue        # equals: the later one breaks
                keep[k] = False
                broken += 1
                break
        cells[index] = own[keep]
    burn = np.zeros((height, width), np.float32)
    for size, own in sorted(zip((f[0] for f in features), cells), key=lambda pair: pair[0]):
        burn[own[:, 0], own[:, 1]] = max(size, 0.001)
    sea = z <= 0.0
    extended = bridged = 0
    for index, (size, line, river, _) in enumerate(features):
        r, c = min(lower[index], key=lambda cell: z[cell])
        if any(sea[cell] for cell in near(r, c)) or any(cover.get(cell, set()) - {index} for cell in near(r, c)):
            continue                # at the sea already, or another feature carries on
        mine = {tuple(cell) for cell in cells[index]}
        others = (burn > 0.0)
        others[tuple(np.array(list(mine)).T)] = False if mine else others[tuple(np.array(list(mine)).T)]
        path = lowest_path(z, others, (r, c), BRIDGE_CELLS)   # a gap to the river it joins
        if path:
            bridged += 1
        else:
            path = lowest_path(z, sea, (r, c), EXTEND_CELLS)   # or the sea it reaches
            if path:
                extended += 1
        for pr, pc in path or []:
            burn[pr, pc] = max(burn[pr, pc], max(size, 0.001))
    print(f"   {len(features)} river lines, {broken} texels broken at divides, {bridged} gaps bridged, {extended} lines carried on to the sea")
    return burn


def lowest_path(z, target, start, limit):
    """The path from `start` to a `target` cell within `limit` steps whose highest ground
    is lowest, the shortest of those (Dijkstra on the running maximum, then the steps), or
    None. The state is the cell and the steps taken to it: keyed by the cell alone, a long
    low route that reached a cell first discarded a shorter, slightly higher one, and when
    its own moves ran out a connection inside the limit was lost. The states grow with
    the limit times the cells within it, small at the limits used here."""
    import heapq
    height, width = z.shape
    best = {(start, 0): z[start]}
    before = {}
    queue = [(z[start], 0, start)]
    while queue:
        top, steps, cell = heapq.heappop(queue)
        if top > best.get((cell, steps), np.inf):
            continue
        if target[cell]:
            path = []
            while steps:
                path.append(cell)
                cell, steps = before[(cell, steps)]
            return [p for p in path if not target[p]]
        if steps == limit:
            continue
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                r, c = cell[0] + dr, (cell[1] + dc) % width
                if not 0 <= r < height:
                    continue
                reach = max(top, z[r, c])
                if reach < best.get(((r, c), steps + 1), np.inf):
                    best[((r, c), steps + 1)] = reach
                    before[((r, c), steps + 1)] = (cell, steps)
                    heapq.heappush(queue, (reach, steps + 1, (r, c)))
    return None


def is_hole(ring):
    """A ring running counter-clockwise in longitude and latitude: a shapefile's inner ring,
    an island in the lake, where its outer rings run clockwise."""
    x, y = np.asarray(ring, float).T
    return float(np.dot(x, np.roll(y, -1)) - np.dot(np.roll(x, -1), y)) > 0.0


def clear_island(inside, ring, scale=8):
    """Clear from the lake mask the texels whose centres the island's ring (in texel
    coordinates) covers. PIL fills every pixel a polygon touches, so drawn at the texel
    size an islet would take its whole texel, and HydroLAKES has 80,000 islands, over a
    thousand each in Huron and the Caspian: drawn `scale` times finer and sampled at the
    texel centres, an island takes the texels it mostly covers and an islet none."""
    height, width = inside.shape
    xy = np.asarray(ring, float)
    c0, r0 = np.maximum(np.floor(xy.min(0)).astype(int), 0)
    c1, r1 = np.minimum(np.floor(xy.max(0)).astype(int) + 1, (width, height))
    if c1 <= c0 or r1 <= r0:
        return
    fine = Image.new("1", ((c1 - c0) * scale, (r1 - r0) * scale), 0)
    ImageDraw.Draw(fine).polygon([((x - c0) * scale, (y - r0) * scale) for x, y in xy], fill=1)
    inside[r0:r1, c0:c1] &= ~np.asarray(fine, bool)[scale // 2::scale, scale // 2::scale]


def lakes(reader, width, height, z):
    """Each lake of LAKE_KM2 or more filled with its mean depth in metres, a texel holding the
    deepest lake covering it, its islands left dry; and the texels of the lakes the grid
    itself holds at or below its datum (the Caspian, the Dead Sea, Kara-Bogaz-Gol), where
    the routing takes the water out of the grid at every sea level, so the Volga still ends
    in the Caspian when the slider stands below 0 m instead of crossing its floor to the
    Manych. Which other lakes are closed (Chad, Balkhash, the Great Salt Lake) the data
    here cannot say: a test on the river lines also closed the Great Lakes and the Volga's
    reservoirs, so those basins keep the routing's own rule and spill."""
    depth = np.zeros((height, width), np.float32)
    closed = np.zeros((height, width), bool)
    for record, shape in zip(reader.iterRecords(fields=["Lake_area", "Depth_avg"]), reader.iterShapes()):
        if record["Lake_area"] < LAKE_KM2:
            continue
        mask = Image.new("1", (width, height), 0)
        draw = ImageDraw.Draw(mask)
        parts = list(shape.parts) + [len(shape.points)]
        rings = [(is_hole(shape.points[start:end]), [to_texel(lon, lat, width, height) for lon, lat in shape.points[start:end]])
                 for start, end in zip(parts, parts[1:]) if end - start >= 3]
        for hole, ring in rings:
            if not hole:
                draw.polygon(ring, fill=1)      # the water: every texel an outer ring touches
        inside = np.array(mask, bool)   # a copy: the islands and the fallback below write into it
        for hole, ring in rings:
            if hole:
                clear_island(inside, ring)
        if not inside.any():   # smaller than a texel: the texel of its first vertex
            x, y = to_texel(*shape.points[0], width, height)
            inside[min(int(y), height - 1), int(x) % width] = True
        np.maximum(depth, np.where(inside, max(record["Depth_avg"], 0.0), 0.0), out=depth)
        closed |= inside & (z <= 0.0)
    return depth, closed


ARRAYS = {"burn": np.float32, "lakes": np.float32, "closed": np.bool_}   # the cache's rasters and their types


def cache_key(z, manifest):
    """What the rasters depend on: the elevation they are cut against and tested for the
    datum, the pinned sources, and the rules that turn them into rasters."""
    digest = hashlib.sha256(np.ascontiguousarray(z).tobytes())
    digest.update(str(z.dtype).encode())
    digest.update(json.dumps(manifest, sort_keys=True).encode())
    digest.update(json.dumps([RULES, LAKE_KM2, RIVER_KINDS, EXTEND_CELLS, BRIDGE_CELLS]).encode())
    return digest.hexdigest()


def load(out, z):
    """The cached rasters for the present grid `z` (the texture-sized elevation), built
    from the verified sources on first use; None when the sources are not fetched or do
    not match the manifest, so the builder can route the present grid unaided. A cache is
    used only when its key, cache_key(), is this grid's, this manifest's and these rules',
    and every array has its shape and type; another grid's or an unreadable one is
    rebuilt, or, without the sources, refused."""
    height, width = z.shape
    cache = out / "paleodem-0000-present-water.npz"
    try:
        manifest = json.loads(MANIFEST.read_text())
    except FileNotFoundError:
        return None
    key = cache_key(z, manifest)
    if cache.exists():
        try:
            with np.load(cache) as data:
                if (str(data["key"]) == key and all(
                        data[name].shape == (height, width) and data[name].dtype == dtype for name, dtype in ARRAYS.items())):
                    return {name: data[name] for name in ARRAYS}
            print(f"   {cache.name} is another grid's, source's or rule's: not used")
        except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
            print(f"   {cache.name} unreadable ({error}): not used")
    try:
        sources = readers(manifest)
    except (FileNotFoundError, ValueError) as error:
        print(f"   present-water sources not fetched or not verified ({error}); the present grid is routed unaided")
        return None
    burn = rivers(sources["rivers"], width, height, z)
    depth, closed = lakes(sources["lakes"], width, height, z)
    np.savez_compressed(cache, key=key, burn=burn, lakes=depth, closed=closed)
    return {"burn": burn, "lakes": depth, "closed": closed}


if __name__ == "__main__":
    import json as _json
    import time
    from scripts.build_paleodem import CATALOGUE, default_source, elevation, locate, resample
    started = time.time()
    catalogue = _json.loads(CATALOGUE.read_text())
    present = next(item for item in catalogue["maps"] if item["age_ma"] == 0)
    grid = resample(elevation(locate(default_source(catalogue), present)), 2048)
    rasters = load(ROOT / "data/derived/paleodem", grid)
    if rasters is None:
        raise SystemExit("sources not fetched; see sources/present-water.json")
    print(f"river texels {(rasters['burn'] > 0).sum()}, closed-lake texels {rasters['closed'].sum()}, "
          f"lake texels {(rasters['lakes'] > 0).sum()}, {time.time() - started:.0f}s")
