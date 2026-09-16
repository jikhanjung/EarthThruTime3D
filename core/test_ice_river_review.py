import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import zipfile

from django.test import SimpleTestCase
from scripts.fetch_paleodem import extract_discardable, verify, verify_extracted
from core.globe import rivers_ice_of


class ExtractedSourceTests(SimpleTestCase):
    def archive(self, root):
        path = root/'source.zip'
        with zipfile.ZipFile(path, 'w') as archive:
            archive.writestr('grids/model.nc', b'grid bytes')
        asset = {'path': str(path), 'bytes': path.stat().st_size,
                 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'members': ['grids/*.nc']}
        return path, asset

    def test_verified_extraction_rejects_missing_and_modified_files(self):
        with TemporaryDirectory() as folder:
            root=Path(folder); archive, asset=self.archive(root); out=root/'extracted'
            verify(archive, asset)
            extract_discardable(archive, out, asset)
            self.assertFalse(archive.exists())
            verify_extracted(out, asset)
            file=out/'grids/model.nc'
            file.write_bytes(b'fake bytes')
            with self.assertRaises(ValueError): verify_extracted(out, asset)
            file.unlink()
            with self.assertRaises(FileNotFoundError): verify_extracted(out, asset)

    def test_partial_extraction_keeps_verified_archive(self):
        with TemporaryDirectory() as folder:
            root=Path(folder); archive, asset=self.archive(root); out=root/'extracted'; out.mkdir()
            with self.assertRaises(FileNotFoundError): extract_discardable(archive, out, asset)
            self.assertTrue(archive.exists())
            with self.assertRaises(FileNotFoundError): verify_extracted(out, asset)

    def test_receipt_from_another_archive_is_rejected(self):
        with TemporaryDirectory() as folder:
            root=Path(folder); archive, asset=self.archive(root); out=root/'extracted'
            extract_discardable(archive, out, asset)
            with self.assertRaises(ValueError): verify_extracted(out, {**asset, 'sha256': '0'*64})


class IceRiverSidecarTests(SimpleTestCase):
    def test_malformed_or_nonmonotonic_sidecar_disables_optional_layer(self):
        with TemporaryDirectory() as folder:
            path=Path(folder)/'rivers-ice.json'
            for data in ['{', '[]', {'slices':[{'lowers':True}]}, {'slices':[
                    {'lowers':True,'age_ka':10,'level_m':-50},
                    {'lowers':True,'age_ka':20,'level_m':-50}]}]:
                path.write_text(data if isinstance(data,str) else json.dumps(data))
                with patch('core.globe.derived_path',return_value=path), self.assertLogs('core.globe'):
                    self.assertIsNone(rivers_ice_of({'id':'paleodem-0000'}))
