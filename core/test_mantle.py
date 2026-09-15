import hashlib
import gzip
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase


class MantleTests(SimpleTestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.override = self.settings(MANTLE_DERIVED_DIR=self.folder, SCOTESE_VIEWER_ENABLED=True)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.content = b'\0' * 48
        self.digest = hashlib.sha256(self.content).hexdigest()
        self.filename = f'slabs-50-{self.digest[:16]}.bin'
        self.item = {'file': self.filename, 'bytes': 48, 'sha256': self.digest,
                     'points': 3, 'indices': 3, 'primitive': 'triangles'}
        self.document = {'schema_version': 1, 'source': 'muller2022-opt1', 'frames': [
            {'index': 50, 'age_ma': 0, 'layers': {n: self.item for n in ('slabs', 'piles', 'boundaries')}}]}

    def install(self):
        (self.folder / 'catalogue.json').write_text(json.dumps(self.document))
        (self.folder / self.filename).write_bytes(self.content)

    def test_missing_and_disabled_data(self):
        response = self.client.get('/mantle/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['frames'], [])
        self.install()
        with self.settings(SCOTESE_VIEWER_ENABLED=False):
            self.assertEqual(self.client.get('/mantle/').context['frames'], [])
            self.assertEqual(self.client.get('/mantle/assets/' + self.filename).status_code, 404)

    def test_original_age_and_verified_asset(self):
        self.install()
        response = self.client.get('/mantle/')
        self.assertEqual(response.context['frames'][0]['age_ma'], 0)
        self.assertContains(response, 'OPT1')
        response = self.client.get('/mantle/assets/' + self.filename)
        self.assertEqual(response.content, self.content)
        self.assertEqual(response['ETag'], f'"{self.digest}"')
        self.assertEqual(self.client.post('/mantle/').status_code, 405)

    def test_unknown_corrupt_and_missing_assets(self):
        self.install()
        self.assertEqual(self.client.get('/mantle/assets/model.zip').status_code, 404)
        other = 'piles-00-0123456789abcdef.bin'
        (self.folder / other).write_bytes(self.content)
        self.assertEqual(self.client.get('/mantle/assets/' + other).status_code, 404)
        (self.folder / self.filename).write_bytes(b'x' * len(self.content))
        self.assertEqual(self.client.get('/mantle/assets/' + self.filename).status_code, 404)
        (self.folder / self.filename).unlink()
        self.assertEqual(self.client.get('/mantle/assets/' + self.filename).status_code, 404)

    def test_precompressed_transfer_and_opt_out(self):
        compressed = gzip.compress(self.content, mtime=0)
        self.item['gzip'] = {'file': self.filename + '.gz', 'bytes': len(compressed),
                             'sha256': hashlib.sha256(compressed).hexdigest()}
        self.install()
        (self.folder / (self.filename + '.gz')).write_bytes(compressed)
        response = self.client.get('/mantle/assets/' + self.filename, HTTP_ACCEPT_ENCODING='br, gzip')
        self.assertEqual(response['Content-Encoding'], 'gzip')
        self.assertEqual(gzip.decompress(response.content), self.content)
        self.assertIn('Accept-Encoding', response['Vary'])
        response = self.client.get('/mantle/assets/' + self.filename, HTTP_ACCEPT_ENCODING='*;q=1,gzip;q=0')
        self.assertNotIn('Content-Encoding', response)
        self.assertEqual(response.content, self.content)
        (self.folder / (self.filename + '.gz')).write_bytes(b'broken')
        self.assertEqual(self.client.get('/mantle/assets/' + self.filename,
                                        HTTP_ACCEPT_ENCODING='gzip').status_code, 404)
