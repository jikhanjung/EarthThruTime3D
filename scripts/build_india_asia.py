"""Extract a fixed 85 E section from OPT1; no flow or crust physics inferred."""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import tempfile
import zipfile

import numpy as np
from PIL import Image

from build_mantle import PREFIX, read_piece, time_mapping
from geodynamics import ROOT, source

LONGITUDE = 85.0
LATITUDES = (-40.0, 60.0)
MAP_BOX = (40.0, 115.0, -40.0, 60.0)


def surface(age):
    """Sample the existing PaleoDEM field into a small regional terrain grid.

    Coordinates remain PALEOMAP, separate from the OPT1 section. Heights include
    bathymetry; the viewer may hold ocean water at zero for its surface rendering.
    """
    path = ROOT / f'data/derived/paleodem/paleodem-{int(age*10):04d}-field.png'
    raw = path.read_bytes()
    with Image.open(path) as image:
        rgb = np.asarray(image.convert('RGB'), dtype=np.float64)
    heights = (rgb[:, :, 1]*16 + rgb[:, :, 2])/4095*15000 - 9000
    nx, ny = 129, 161
    longitude = np.linspace(MAP_BOX[0], MAP_BOX[1], nx)
    latitude = np.linspace(MAP_BOX[3], MAP_BOX[2], ny)
    cols = (longitude+180)/360*rgb.shape[1]-.5
    rows = (90-latitude)/180*rgb.shape[0]-.5
    left = np.floor(cols).astype(int); top = np.floor(rows).astype(int)
    u = cols-left; v = (rows-top)[:, None]
    a = heights[top[:, None], left]*(1-u) + heights[top[:, None], left+1]*u
    b = heights[(top+1)[:, None], left]*(1-u) + heights[(top+1)[:, None], left+1]*u
    sampled = a*(1-v) + b*v
    return {'source': 'Scotese & Wright 2018 PaleoDEM / PALEOMAP', 'frame_id': path.stem.removesuffix('-field'),
            'field_sha256': hashlib.sha256(raw).hexdigest(), 'nx': nx, 'ny': ny, 'bounds': MAP_BOX,
            'heights_m': np.round(sampled).astype(int).ravel().tolist(),
            'sampling': 'bilinear regional display grid; rounding does not increase source precision'}


def clip_segment(a, b, box):
    """Liang–Barsky in display coordinates, preserving crossings from outside."""
    xmin, xmax, ymin, ymax = box
    dx, dy = b[0] - a[0], b[1] - a[1]
    lo, hi = 0., 1.
    for p, q in ((-dx, a[0]-xmin), (dx, xmax-a[0]), (-dy, a[1]-ymin), (dy, ymax-a[1])):
        if abs(p) < 1e-12:
            if q < 0:
                return None
        elif p < 0:
            lo = max(lo, q/p)
        else:
            hi = min(hi, q/p)
        if lo > hi:
            return None
    return [a[0]+lo*dx, a[1]+lo*dy, a[0]+hi*dx, a[1]+hi*dy]


def section_segments(points, indices, longitude=LONGITUDE):
    """Intersect triangles with a meridian plane, selecting its positive half-plane.

    Fully coplanar triangles are skipped (a non-unique surface section); a tangent
    vertex alone is not a segment. Shared-edge results are deduplicated downstream.
    """
    angle = math.radians(longitude)
    horizontal = np.array([math.cos(angle), math.sin(angle), 0])
    normal = np.array([-math.sin(angle), math.cos(angle), 0])
    distances = points @ normal
    triangles = np.asarray(indices).reshape(-1, 3)
    signed = distances[triangles]
    candidates = triangles[(signed.min(axis=1) <= 1e-10) & (signed.max(axis=1) >= -1e-10)]
    result = []
    for triangle in candidates:
        vertices = points[triangle]
        d = distances[triangle]
        if np.all(np.abs(d) <= 1e-10):
            continue
        hits = []
        for i, j in ((0, 1), (1, 2), (2, 0)):
            if abs(d[i]) <= 1e-10:
                hits.append(vertices[i])
            if d[i] * d[j] < 0 and abs(d[i]) > 1e-10 and abs(d[j]) > 1e-10:
                hits.append(vertices[i] + (vertices[j]-vertices[i]) * d[i]/(d[i]-d[j]))
        unique = {tuple(np.round(p, 10)): p for p in hits}
        if len(unique) != 2:
            continue
        a, b = unique.values()
        if min(a @ horizontal, b @ horizontal) <= 0:
            continue
        def project(p):
            return [math.degrees(math.atan2(p[2], p @ horizontal)), (1 - np.linalg.norm(p))*6371]
        segment = clip_segment(project(a), project(b), (*LATITUDES, 0, 2900))
        if segment is not None:
            result.append([round(x, 4 if i % 2 == 0 else 3) for i, x in enumerate(segment)])
    return result


def map_segments(points, indices):
    longitude = np.degrees(np.arctan2(points[:, 1], points[:, 0]))
    latitude = np.degrees(np.arctan2(points[:, 2], np.hypot(points[:, 0], points[:, 1])))
    coordinates = np.column_stack((longitude, latitude))
    result = []
    for pair in np.asarray(indices).reshape(-1, 2):
        a, b = coordinates[pair]
        if abs(a[0] - b[0]) > 180:
            continue  # This regional map does not cross the antimeridian.
        segment = clip_segment(a, b, MAP_BOX)
        if segment is not None:
            result.append([round(v, 4) for v in segment])
    return result


def unique_segments(segments):
    return [list(k) for k in sorted({min(tuple(s), tuple(s[2:] + s[:2])) for s in segments})]


def build(output):
    document, archive = source('muller2022-opt1')
    result = {'schema_version': 1, 'source': document['id'], 'kind': 'published_simulation_section',
              'longitude': LONGITUDE, 'latitude_range': LATITUDES, 'map_box': MAP_BOX,
              'max_depth_km': 2900, 'reference_frame': document['reference_frame'],
              'source_archive_sha256': next(a['sha256'] for a in document['assets'] if a['role'] == 'archive'),
              'sampling': 'original frames only; fixed spatial section, not a material trajectory',
              'frames': []}
    with zipfile.ZipFile(archive) as bundle:
        scale, shift = time_mapping(bundle)
        for index in range(46, 51):
            frame = {'index': index, 'age_ma': shift + scale*index, 'section': {}, 'map': {}}
            frame['surface'] = surface(frame['age_ma'])
            for layer, title in [('slabs', 'Slabs'), ('piles', 'Piles')]:
                import xml.etree.ElementTree as ET
                parent = PREFIX + f'{title}/{title}_{index:02d}.pvtu'
                root = ET.fromstring(bundle.read(parent))
                segments = []
                for member in root.findall('.//Piece'):
                    relative = PurePosixPath(member.get('Source'))
                    if relative.is_absolute() or '..' in relative.parts:
                        raise ValueError('Unsafe member')
                    path = str(PurePosixPath(parent).parent / relative)
                    p, cells, _, time = read_piece(bundle.read(path), 'triangles')
                    if time != index:
                        raise ValueError('Source time mismatch')
                    segments.extend(section_segments(p, cells))
                frame['section'][layer] = unique_segments(segments)
            for layer, path in [('cratons', f'Reconstruction/Cratons/Cratons_gcm32__{index:02d}.vtu'),
                                ('boundaries', f'Reconstruction/Plate-polygons/PlateBoundaries_gcm32__{index:02d}.vtu')]:
                p, cells, _, _ = read_piece(bundle.read(PREFIX + path), 'lines')
                frame['map'][layer] = map_segments(p, cells)
            result['frames'].append(frame)
            print(f"{frame['age_ma']:g} Ma: {sum(map(len, frame['section'].values()))} section segments")
    raw = (json.dumps(result, separators=(',', ':'), allow_nan=False) + '\n').encode()
    compressed = gzip.compress(raw, compresslevel=6, mtime=0)
    digest = hashlib.sha256(raw).hexdigest()
    name = f'section-{digest[:16]}.json'
    metadata = {'schema_version': 1, 'source': document['id'], 'file': name, 'bytes': len(raw), 'sha256': digest,
                'gzip': {'file': name+'.gz', 'bytes': len(compressed), 'sha256': hashlib.sha256(compressed).hexdigest()}}
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output, prefix='.build-') as staging:
        folder = Path(staging)
        (folder/name).write_bytes(raw)
        (folder/(name+'.gz')).write_bytes(compressed)
        (folder/'catalogue.json').write_text(json.dumps(metadata, indent=2)+'\n')
        for asset in (name, name+'.gz', 'catalogue.json'):
            (folder/asset).replace(output/asset)
    print(f'All five frames: {len(raw)} bytes, gzip {len(compressed)} bytes -> {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'data/derived/india-asia')
    build(parser.parse_args().output)
