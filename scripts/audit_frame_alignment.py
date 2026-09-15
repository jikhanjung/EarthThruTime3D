"""Audit OPT1 craton trajectories against pinned plate rotations, without fitting terrain.

Writes diagnostic transforms only. No runtime catalogue or geometry is changed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET
import zipfile

import numpy as np
from scipy.spatial import cKDTree

from build_mantle import PREFIX, read_piece, time_mapping
from fetch_paleodem import verify
from geodynamics import ROOT, NS, source
from rotation_model import RotationModel
from frame_alignment import (apply, fit_rotation, lonlat_xyz, unit, quaternion_matrix,
                             rotation_degrees, separation_degrees)

AGES = [80, 60, 40, 20, 0]
# Curated comparison of stable interiors, not equivalence of polygon extents.
PLATES = {701: ('Africa', 701), 501: ('India', 501), 5011: ('India internal block', 501),
          302: ('Baltica', 302), 401: ('Siberia', 401), 801: ('Australia', 801),
          101: ('North America', 101), 201: ('South America', 201)}
MATCH_DEG = .001  # ~111 m: identify shared vertices, not geological accuracy.
RIGID_DEG = .01   # ~1.11 km: held-out geometric trajectory consistency.
FRAME_DEG = .1    # ~11.1 km: strict visual co-location screen, not confidence interval.


def stats(values):
    return {k: float(v) for k, v in zip(['median_deg', 'p95_deg', 'max_deg'],
                                      [np.median(values), np.percentile(values, 95), np.max(values)])}


def plate_source(model, temporary):
    manifest_path = ROOT / 'sources/plate-models' / f'{model}.json'
    doc = json.loads(manifest_path.read_text())
    archive = ROOT / doc['archive']['path']
    verify(archive, doc['archive'])
    with zipfile.ZipFile(archive) as z:
        member = next(m for m in doc['members'] if m['role'] == 'rotation')
        data = z.read(doc['archive']['member_prefix'] + member['name'])
        if len(data) != member['bytes'] or hashlib.sha256(data).hexdigest() != member['sha256']:
            raise ValueError('Rotation member hash mismatch')
        path = temporary / f'{model}.rot'
        path.write_bytes(data)
        extra = z.read('Cratons/shapes_cratons_Merdith_etal.gpml') if model == 'muller2022' else None
    return RotationModel(path), {'manifest': str(manifest_path.relative_to(ROOT)),
                                'archive_sha256': doc['archive']['sha256'],
                                'rotation_member': member['name'], 'rotation_sha256': member['sha256']}, extra


def match_vertices(gpml, present):
    tree = cKDTree(unit(present))
    candidates = {pid: set() for pid in PLATES}
    counts = {pid: 0 for pid in PLATES}
    for feature in ET.fromstring(gpml).findall('gml:featureMember', NS):
        pid = int(feature.findtext('.//gpml:reconstructionPlateId//gpml:value', default='-1', namespaces=NS))
        if pid not in PLATES:
            continue
        for element in feature.findall('.//gml:posList', NS):
            ll = np.asarray(element.text.split(), float).reshape(-1, 2)
            xyz = lonlat_xyz(ll[:, 1], ll[:, 0])
            distance, index = tree.query(xyz)
            good = distance <= 2*np.sin(np.deg2rad(MATCH_DEG)/2)
            candidates[pid].update(index[good].tolist())
            counts[pid] += len(index)
    # Shared-border vertices with conflicting plate assignment cannot be tracers.
    owners = {}
    for pid, indices in candidates.items():
        for i in indices:
            owners.setdefault(i, set()).add(pid)
    result = {pid: np.array(sorted(i for i in indices if len(owners[i]) == 1), dtype=int)
              for pid, indices in candidates.items()}
    if any(len(v) < 20 for v in result.values()):
        raise ValueError(f'Insufficient matched plate tracers: {[(k,len(v)) for k,v in result.items()]}')
    return result, counts


def trajectory_fit(present, observed, ids):
    """Use index matches as hypotheses, then verify held-out geometry spatially.

    VTU cell ordering changes and identical present vertices can have several IDs.
    Deterministic consensus rejects those ambiguous index matches. No plate-model
    rotation is used to identify the source trajectory.
    """
    train, held = ids[::2], ids[1::2]
    rng = np.random.default_rng(20260915)
    best = np.zeros(len(train), dtype=bool)
    for _ in range(256):
        sample = rng.choice(train, 3, replace=False)
        try:
            candidate = fit_rotation(present[sample], observed[sample])
        except ValueError:
            continue
        good = separation_degrees(apply(candidate, present[train]), observed[train]) < RIGID_DEG
        if good.sum() > best.sum():
            best = good
    if best.mean() <= .5:
        raise ValueError(f'No majority of training index matches constrain one rigid rotation: {best.mean()}')
    rotation = fit_rotation(present[train[best]], observed[train[best]])
    tree = cKDTree(observed)
    _, nearest = tree.query(apply(rotation, present[held]))
    errors = separation_degrees(apply(rotation, present[held]), observed[nearest])
    if np.max(errors) > RIGID_DEG:
        raise ValueError(f'Held-out shape does not support rigid trajectory: {stats(errors)}')
    _, all_nearest = tree.query(apply(rotation, present[ids]))
    full_errors = separation_degrees(apply(rotation, present[ids]), observed[all_nearest])
    if np.max(full_errors) > RIGID_DEG:
        raise ValueError('Not all selected vertices support the fitted trajectory')
    return rotation, observed[all_nearest], {'held_out_rigid_fit': stats(errors),
        'training_index_inlier_fraction': float(best.mean()),
        'held_out_vertices': len(held), 'full_spatial_fit': stats(full_errors),
        'spatial_rematch_count': int(np.sum(ids != all_nearest))}


def audit(output):
    doc, archive = source('muller2022-opt1')
    with tempfile.TemporaryDirectory() as temp, zipfile.ZipFile(archive) as z:
        muller, mprov, gpml = plate_source('muller2022', Path(temp))
        paleo, pprov, _ = plate_source('paleomap2016', Path(temp))
        scale, shift = time_mapping(z)
        def read(age):
            frame = int((age-shift)/scale)
            member = PREFIX + f'Reconstruction/Cratons/Cratons_gcm32__{frame:02d}.vtu'
            raw = z.read(member)
            points, edges, _, _ = read_piece(raw, 'lines')
            return unit(points), edges, {'member': member, 'sha256': hashlib.sha256(raw).hexdigest()}
        present, topology, _ = read(0)
        matches, candidates = match_vertices(gpml, present)
        report = {'schema_version': 1, 'kind': 'diagnostic_only', 'runtime_alignment_approved': False,
                  'ages_ma': AGES, 'mapping_scope': 'Sampled ages only; eight tested plate interiors; no interpolation or terrain alignment',
                  'craton_member': 'Cratons/shapes_cratons_Merdith_etal.gpml', 'thresholds_deg': {'vertex_match': MATCH_DEG, 'held_out_rigidity': RIGID_DEG,
                                                   'frame_colocation': FRAME_DEG},
                  'sources': {'opt1_archive_sha256': doc['assets'][0]['sha256'], 'muller2022': mprov,
                              'paleomap2016': pprov, 'cratons_gpml_sha256': hashlib.sha256(gpml).hexdigest()},
                  'plates': {str(pid): {'label': name, 'paleomap_proxy_id': target,
                                      'matched_unique_vertices': len(matches[pid]), 'gpml_vertices': candidates[pid]}
                             for pid, (name, target) in PLATES.items()}, 'frames': []}
        for age in AGES:
            observed, edges, provenance = read(age)
            if observed.shape != present.shape:
                raise ValueError('Craton index/topology changed; point correspondence must be re-established')
            fits, row = {}, {'age_ma': age, 'source': provenance, 'plates': {}}
            paired = {}
            for pid, ids in matches.items():
                try:
                    rotation, paired[pid], evidence = trajectory_fit(present, observed, ids)
                except ValueError as error:
                    raise ValueError(f'{age} Ma plate {pid}: {error}') from error
                fits[pid] = rotation
                row['plates'][str(pid)] = evidence
            row['connectivity_identical'] = bool(np.array_equal(edges, topology))
            row['correspondence_pass'] = True
            # Africa anchoring is explicit and reproducible, not an optimised visual fit.
            source_to_muller = quaternion_matrix(muller.rotation(701, age)) @ fits[701].T
            source_to_paleo = quaternion_matrix(paleo.rotation(701, age)) @ fits[701].T
            row['africa_anchor'] = {'opt1_to_muller_matrix': source_to_muller.tolist(),
                                    'opt1_to_paleomap_matrix': source_to_paleo.tolist(),
                                    'muller_angle_deg': rotation_degrees(source_to_muller),
                                    'paleomap_angle_deg': rotation_degrees(source_to_paleo)}
            for pid, ids in matches.items():
                mr = quaternion_matrix(muller.rotation(pid, age))
                pr = quaternion_matrix(paleo.rotation(PLATES[pid][1], age))
                a, b = present[ids], paired[pid]
                item = row['plates'][str(pid)]
                item.update({'muller_direct': stats(separation_degrees(b, apply(mr, a))),
                             'muller_after_anchor': stats(separation_degrees(apply(source_to_muller, b), apply(mr, a))),
                             'paleomap_direct': stats(separation_degrees(b, apply(pr, a))),
                             'paleomap_after_anchor': stats(separation_degrees(apply(source_to_paleo, b), apply(pr, a))),
                             'muller_rotation_residual_deg': rotation_degrees(mr @ (source_to_muller @ fits[pid]).T),
                             'paleomap_rotation_residual_deg': rotation_degrees(pr @ (source_to_paleo @ fits[pid]).T)})
                # Thin each independently to keep the interactive diagnostic small.
                sample = np.arange(len(ids))[::max(1, len(ids)//100)]
                item['preview'] = {'opt1': b[sample].round(7).tolist(),
                                   'muller': apply(mr, a[sample]).round(7).tolist(),
                                   'paleomap': apply(pr, a[sample]).round(7).tolist()}
            row['muller_anchor_screen_pass'] = all(p['muller_rotation_residual_deg'] <= FRAME_DEG for p in row['plates'].values())
            row['paleomap_anchor_screen_pass'] = all(p['paleomap_rotation_residual_deg'] <= FRAME_DEG for p in row['plates'].values())
            report['frames'].append(row)
    output.mkdir(parents=True, exist_ok=True)
    (output/'report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n')
    template = (ROOT/'scripts/frame_alignment_preview.html').read_text()
    (output/'preview.html').write_text(template.replace('REPORT_JSON', json.dumps(report, ensure_ascii=False).replace('<', '\\u003c')))
    print('age | OPT1→Müller Africa angle | max residual | OPT1→PALEOMAP Africa angle | max residual')
    for row in report['frames']:
        print(row['age_ma'], *(round(v, 6) for v in [row['africa_anchor']['muller_angle_deg'],
              max(p['muller_rotation_residual_deg'] for p in row['plates'].values()),
              row['africa_anchor']['paleomap_angle_deg'],
              max(p['paleomap_rotation_residual_deg'] for p in row['plates'].values())]))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'data/derived/frame-alignment')
    parser.add_argument('--record', type=Path, help='Write compact review snapshot without preview point arrays')
    args = parser.parse_args()
    report = audit(args.output)
    if args.record:
        for frame in report['frames']:
            for plate in frame['plates'].values():
                plate.pop('preview')
        args.record.parent.mkdir(parents=True, exist_ok=True)
        args.record.write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n')
