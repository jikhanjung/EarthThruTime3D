"""Offline synthetic checks for VTK decoding and topology; needs processing requirements."""
import base64
import hashlib
import json
from tempfile import TemporaryDirectory
from unittest.mock import patch
from pathlib import Path
import struct
import sys
import unittest
import xml.etree.ElementTree as ET
import zlib

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from build_mantle import array, read_piece
from geodynamics import gpml_summary, source


def node(name, values, dtype, vtk_type):
    data = np.array(values, dtype=dtype).tobytes()
    result = ET.Element('DataArray', Name=name, type=vtk_type, format='binary')
    result.text = base64.b64encode(struct.pack('<Q', len(data)) + data).decode()
    return result


def mesh(indices=(0, 1, 2), cell_type=5):
    root = ET.Element('VTKFile', type='UnstructuredGrid', byte_order='LittleEndian', header_type='UInt64')
    grid = ET.SubElement(root, 'UnstructuredGrid')
    piece = ET.SubElement(grid, 'Piece', NumberOfPoints='3', NumberOfCells='1')
    points = ET.SubElement(piece, 'Points')
    points.append(node('Points', [1, 0, 0, 0, 1, 0, 0, 0, 1], '<f4', 'Float32'))
    cells = ET.SubElement(piece, 'Cells')
    cells.append(node('connectivity', indices, '<i8', 'Int64'))
    cells.append(node('offsets', [len(indices)], '<i8', 'Int64'))
    cells.append(node('types', [cell_type], 'u1', 'UInt8'))
    return root


class VTKTests(unittest.TestCase):
    def test_triangle_and_polyline_connectivity(self):
        points, indices, _, _ = read_piece(ET.tostring(mesh()), 'triangles')
        np.testing.assert_array_equal(points, np.eye(3))
        np.testing.assert_array_equal(indices, [0, 1, 2])
        _, lines, _, _ = read_piece(ET.tostring(mesh(cell_type=4)), 'lines')
        np.testing.assert_array_equal(lines, [0, 1, 1, 2])

    def test_invalid_topology_and_header_rejected(self):
        for root in (mesh(indices=(-1, 1, 2)), mesh(indices=(0, 1, 3)), mesh(cell_type=9)):
            with self.assertRaises(ValueError):
                read_piece(ET.tostring(root), 'triangles')
        root = mesh()
        root.find('.//Points/DataArray').text = base64.b64encode(struct.pack('<Q', 999)).decode()
        with self.assertRaises(ValueError):
            read_piece(ET.tostring(root), 'triangles')

    def test_meshio_compressed_blocks(self):
        chunks = [struct.pack('<dd', 1, 2), struct.pack('<d', 3)]
        compressed = [zlib.compress(x) for x in chunks]
        header = struct.pack('<IIIII', 2, 16, 8, *map(len, compressed))
        root = ET.Element('VTKFile', byte_order='LittleEndian', compressor='vtkZLibDataCompressor')
        item = ET.Element('DataArray', type='Float64', format='binary')
        item.text = base64.b64encode(header).decode() + base64.b64encode(b''.join(compressed)).decode()
        np.testing.assert_array_equal(array(item, root), [1, 2, 3])

    def test_nonfinite_rejected(self):
        root = mesh()
        with self.assertRaises(ValueError):
            array(node('bad', [float('nan')], '<f4', 'Float32'), root)

    def test_nested_network_is_not_double_counted(self):
        data = b'''<gpml:FeatureCollection xmlns:gpml="http://www.gplates.org/gplates" xmlns:gml="http://www.opengis.net/gml">
          <gml:featureMember><gpml:TopologicalNetwork><gml:name>India</gml:name>
            <gpml:network><gpml:TopologicalNetwork/></gpml:network>
          </gpml:TopologicalNetwork></gml:featureMember></gpml:FeatureCollection>'''
        summary = gpml_summary(data)
        self.assertEqual(summary['feature_types'], {'TopologicalNetwork': 1})
        self.assertEqual(len(summary['networks']), 1)


class SourceIntegrityTests(unittest.TestCase):
    def test_mutable_record_is_optional_but_archive_integrity_is_required(self):
        manifest = json.loads((Path(__file__).resolve().parents[1] /
                               'sources/geodynamics/muller2022-opt1.json').read_text())
        with TemporaryDirectory() as folder:
            root = Path(folder)
            pinned = root/'sources/geodynamics/muller2022-opt1.json'
            pinned.parent.mkdir(parents=True)
            for asset in manifest['assets']:
                path = root/asset['path']
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'verified source')
                asset.update(bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
            pinned.write_text(json.dumps(manifest))
            record = root/'data/sources/geodynamics/muller2022-opt1/record.json'
            with patch('geodynamics.ROOT', root), patch('geodynamics.SOURCES', root/'data/sources'):
                _, archive = source('muller2022-opt1')
                self.assertFalse(record.exists())
                record.write_text('{"stats":{"views":100000}}')
                source('muller2022-opt1')
                archive.write_bytes(b'corrupted bytes')
                with self.assertRaises(ValueError):
                    source('muller2022-opt1')


if __name__ == '__main__':
    unittest.main()
