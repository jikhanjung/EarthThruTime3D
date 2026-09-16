"""Build a small present-day CRUST 2.0 display grid from a pinned EarthByte ZIP.

Usage: .venv/bin/python scripts/build_crust.py --archive PATH
No network access. Outputs south-to-north, west-to-east cell centres, little-endian
uint16 in 0.01 km units (65535 missing). Sampling is not new scientific resolution.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

import numpy as np
from netCDF4 import Dataset

ROOT = Path(__file__).resolve().parents[1]


def pack_grid(lon, lat, z):
    if z.shape != (5401, 10801) or not np.allclose(lon, np.linspace(-180, 180, 10801)) or not np.allclose(lat, np.linspace(-90, 90, 5401)):
        raise ValueError('Unexpected source coordinates')
    if not np.ma.allclose(z[:, 0], z[:, -1]):
        raise ValueError('Longitude seam differs')
    # Every 1-degree centre coincides with a source node. Do not introduce another
    # averaging kernel across the continent/ocean transition.
    sampled = np.ma.asarray(z[15:5400:30, 15:10800:30])
    valid = ~np.ma.getmaskarray(sampled) & np.isfinite(sampled.filled(np.nan))
    if np.any((sampled.data[valid] < 0) | (sampled.data[valid] > 80)):
        raise ValueError('Thickness outside the published legend')
    result = np.full((180, 360), 65535, dtype='<u2')
    result[valid] = np.rint(sampled.data[valid] * 100).astype('<u2')
    return result


def build(archive, output, raw):
    source = json.loads((ROOT / 'sources/crust/crust2.json').read_text())
    blob = archive.read_bytes()
    if len(blob) != source['bytes'] or hashlib.sha256(blob).hexdigest() != source['sha256']:
        raise ValueError('Source archive does not match pinned bytes/hash')
    with zipfile.ZipFile(archive) as bundle:
        if bundle.testzip() is not None:
            raise ValueError('Corrupt source ZIP')
        license_text = bundle.read(source['license_member']).decode()
        if 'Creative Commons Attribution 4.0' not in license_text:
            raise ValueError('Unexpected distribution license')
        with Dataset('crust', memory=bundle.read(source['member'])) as ds:
            packed = pack_grid(ds['lon'][:], ds['lat'][:], ds['z'][:])
    raw.mkdir(parents=True, exist_ok=True)
    target = raw / 'Crustal_Thickness.zip'
    if archive.resolve() != target.resolve():
        shutil.copyfile(archive, target)
    (raw / 'License.txt').write_text(license_text)
    output.mkdir(parents=True, exist_ok=True)
    data = packed.tobytes()
    digest = hashlib.sha256(data).hexdigest()
    name = f'crust2-{digest[:16]}.bin'
    (output / name).write_bytes(data)
    compressed = gzip.compress(data, mtime=0)
    (output / (name + '.gz')).write_bytes(compressed)
    catalogue = {
        'schema_version': 1, 'source': source['id'], 'source_sha256': source['sha256'],
        'width': 360, 'height': 180, 'unit_km': 0.01, 'missing': 65535,
        'order': 'south-to-north, west-to-east, cell-centred',
        'sampling': 'Source nodes at 1-degree cell centres; source model 2 degrees.',
        'asset': {'file': name, 'bytes': len(data), 'sha256': digest,
                  'gzip': {'file': name + '.gz', 'bytes': len(compressed),
                           'sha256': hashlib.sha256(compressed).hexdigest()}},
    }
    (output / 'catalogue.json').write_text(json.dumps(catalogue, indent=2) + '\n')
    print(json.dumps(catalogue, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT / 'data/derived/crust')
    parser.add_argument('--raw', type=Path, default=ROOT / 'data/raw/crust')
    args = parser.parse_args()
    build(args.archive, args.output, args.raw)
