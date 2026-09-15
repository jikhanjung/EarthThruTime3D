import gzip
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase


class CollisionTests(SimpleTestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        override = self.settings(INDIA_ASIA_DERIVED_DIR=self.path, SCOTESE_VIEWER_ENABLED=True)
        override.enable()
        self.addCleanup(override.disable)

    def install(self):
        content = b'{"schema_version":1,"frames":[]}'
        sha = hashlib.sha256(content).hexdigest()
        name = f'section-{sha[:16]}.json'
        compressed = gzip.compress(content, mtime=0)
        doc = {'schema_version': 1, 'source': 'muller2022-opt1', 'file': name,
               'bytes': len(content), 'sha256': sha,
               'gzip': {'file': name+'.gz', 'bytes': len(compressed),
                        'sha256': hashlib.sha256(compressed).hexdigest()}}
        (self.path/name).write_bytes(content)
        (self.path/(name+'.gz')).write_bytes(compressed)
        (self.path/'catalogue.json').write_text(json.dumps(doc))
        return '/collision/data/'+sha[:16]+'.json', name, content

    def test_lazy_modal_and_missing_data(self):
        response = self.client.get('/about/')
        self.assertContains(response, 'id="collision-dialog"')
        self.assertContains(response, 'data-src="/collision/"')
        self.assertNotContains(response, 'src="/collision/" title=')
        self.assertIsNone(self.client.get('/collision/').context['data_url'])

    def test_verified_compressed_data_and_disabled_viewer(self):
        url, name, content = self.install()
        self.assertEqual(self.client.get('/collision/').context['data_url'], url)
        self.assertEqual(self.client.get('/collision/')['X-Frame-Options'], 'SAMEORIGIN')
        response = self.client.get(url, HTTP_ACCEPT_ENCODING='gzip')
        self.assertEqual(gzip.decompress(response.content), content)
        self.assertEqual(response['Content-Encoding'], 'gzip')
        self.assertEqual(self.client.get(url, HTTP_ACCEPT_ENCODING='gzip;q=0').content, content)
        with self.settings(SCOTESE_VIEWER_ENABLED=False):
            self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.get('/collision/data/wrong.json').status_code, 404)
        (self.path/name).write_bytes(b'corrupt')
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post('/collision/').status_code, 405)
