import gzip
import hashlib
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from django.conf import settings
from django.test import SimpleTestCase, override_settings

from core.crust import globe_config
from deploy.pack_data import pack_crust


class CrustTests(SimpleTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.override = override_settings(CRUST_DERIVED_DIR=self.root, SCOTESE_VIEWER_ENABLED=True)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.blob = b'\0' * 129600
        digest = hashlib.sha256(self.blob).hexdigest()
        self.name = f'crust2-{digest[:16]}.bin'
        self.url = f'/crust/assets/{self.name}'
        compressed = gzip.compress(self.blob, mtime=0)
        source = json.loads((settings.BASE_DIR / 'sources/crust/crust2.json').read_text())
        self.data = {
            'schema_version': 1, 'source': source['id'], 'source_sha256': source['sha256'],
            'width': 360, 'height': 180, 'unit_km': .01, 'missing': 65535,
            'asset': {'file': self.name, 'bytes': len(self.blob), 'sha256': digest,
                      'gzip': {'file': self.name + '.gz', 'bytes': len(compressed),
                               'sha256': hashlib.sha256(compressed).hexdigest()}},
        }
        (self.root / self.name).write_bytes(self.blob)
        (self.root / (self.name + '.gz')).write_bytes(compressed)
        self.save()

    def save(self):
        (self.root / 'catalogue.json').write_text(json.dumps(self.data))

    def test_verified_compressed_asset_and_etag(self):
        response = self.client.get(self.url, HTTP_ACCEPT_ENCODING='gzip')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(gzip.decompress(b''.join(response.streaming_content)), self.blob)
        self.assertEqual(response['Content-Encoding'], 'gzip')
        cached = self.client.get(self.url, HTTP_ACCEPT_ENCODING='gzip', HTTP_IF_NONE_MATCH=response['ETag'])
        self.assertEqual(cached.status_code, 304)

    def test_same_size_tamper_is_rejected(self):
        (self.root / self.name).write_bytes(b'x' * 129600)
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_bad_schema_source_and_path_hide_optional_data(self):
        for key, value in [('width', 720), ('unit_km', 1), ('source_sha256', 'bad')]:
            original = self.data[key]
            self.data[key] = value
            self.save()
            self.assertIsNone(globe_config())
            self.data[key] = original
        self.data['asset']['file'] = '../outside.bin'
        self.save()
        self.assertIsNone(globe_config())

    def test_missing_or_disabled(self):
        with override_settings(SCOTESE_VIEWER_ENABLED=False):
            self.assertIsNone(globe_config())
            self.assertEqual(self.client.get(self.url).status_code, 404)
        (self.root / self.name).unlink()
        self.assertIsNone(globe_config())

    def test_release_packs_only_verified_derivatives(self):
        project = self.root / 'project'
        source = project / 'sources/crust'
        source.mkdir(parents=True)
        (source / 'crust2.json').write_bytes((settings.BASE_DIR / 'sources/crust/crust2.json').read_bytes())
        derived = project / 'data/derived/crust'
        derived.mkdir(parents=True)
        for name in ['catalogue.json', self.name, self.name + '.gz']:
            (derived / name).write_bytes((self.root / name).read_bytes())
        (derived / 'unlisted.zip').write_bytes(b'not published')
        files = []
        with patch('deploy.pack_data.BASE_DIR', project):
            pack_crust(project / 'stage', files)
            self.assertEqual(len(files), 3)
            self.assertFalse((project / 'stage/crust/unlisted.zip').exists())
            (derived / (self.name + '.gz')).write_bytes(b'corrupt')
            with self.assertRaises(ValueError):
                pack_crust(project / 'stage2', [])
