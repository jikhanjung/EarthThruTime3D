import json
import re
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import SimpleTestCase

from config.version import VERSION



class OptionalDataTests(SimpleTestCase):
    def test_malformed_catalogues_disable_only_optional_views(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            with self.settings(MANTLE_DERIVED_DIR=root, INDIA_ASIA_DERIVED_DIR=root,
                               SCOTESE_VIEWER_ENABLED=True):
                for raw in ['{', '[]', '{}', '{"schema_version":2}',
                            '{"schema_version":1,"source":"muller2022-opt1","frames":[{}]}']:
                    with self.subTest(raw=raw):
                        (root/'catalogue.json').write_text(raw)
                        with self.assertLogs('core.experiment_assets', level='WARNING'):
                            home = self.client.get('/')
                            mantle = self.client.get('/mantle/')
                            collision = self.client.get('/collision/')
                        self.assertEqual(home.status_code, 200)
                        self.assertIsNone(home.context['mantle_overlay'])
                        self.assertEqual(mantle.context['frames'], [])
                        self.assertIsNone(collision.context['data_url'])
                        with self.assertLogs('core.experiment_assets', level='WARNING'):
                            self.assertEqual(self.client.get('/collision/data/0123456789abcdef.json').status_code, 404)

    def test_missing_overlay_config_does_not_break_home(self):
        with patch('core.mantle.read_json', side_effect=FileNotFoundError):
            with self.assertLogs('core.experiment_assets', level='WARNING'):
                response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context['mantle_overlay'])

    def test_dialog_is_limited_to_viewer_documents_and_map_precedes_modules(self):
        for url in ['/about/', '/privacy/', '/contact/']:
            self.assertNotContains(self.client.get(url), 'collision-dialog')
        html = self.client.get('/').content.decode()
        self.assertIn('data-src="/collision/"', html)
        self.assertLess(html.index('type="importmap"'), html.index('type="module"'))


    def test_mantle_module_contracts_share_the_release_cache_version(self):
        html = self.client.get('/').content.decode()
        imports = json.loads(re.search(r'<script type="importmap">(.*?)</script>', html).group(1))['imports']
        for name in ('mantle-overlay', 'mantle-scene'):
            path = f'/static/core/{name}.js'
            self.assertEqual(imports[path], f'{path}?v={VERSION}')
