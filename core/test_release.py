import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import SimpleTestCase

from deploy.host.update_compose_env import updated
from deploy.pack_data import pack_experiments


class ReleaseTests(SimpleTestCase):
    def test_existing_compose_configuration_survives(self):
        original = '# local settings\nIMAGE_TAG=v0.10.5\nDATA_VERSION=v0.10.5\nHOST_PORT=8999\nEXTRA=value\n'
        result = updated(original, 'v0.11.0')
        self.assertIn('EXTRA=value\n', result)
        self.assertIn('HOST_PORT=8999\n', result)
        self.assertIn('IMAGE_TAG=v0.11.0\n', result)
        self.assertIn('DATA_VERSION=v0.11.0\n', result)
        self.assertIn('# local settings\n', result)
        self.assertIn('HOST_PORT=8014\n', updated('', 'v0.11.0'))
        self.assertIn('HOST_PORT=8001\n', updated(original, 'v0.11.0', '8001'))

    def test_missing_frames_and_tampered_mesh_fail_before_release(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root/'data/derived/mantle/muller2022-opt1'
            folder.mkdir(parents=True)
            content = b'valid'; (folder/'mesh.bin').write_bytes(content)
            asset = {'file': 'mesh.bin', 'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest()}
            asset['gzip'] = {k: v for k, v in asset.items()}
            doc = {'schema_version': 1, 'source': 'muller2022-opt1', 'frames': []}
            (folder/'catalogue.json').write_text(json.dumps(doc))
            with patch('deploy.pack_data.BASE_DIR', root):
                with self.assertRaisesRegex(ValueError, '51 mantle'):
                    pack_experiments(root/'stage', [])
                doc['frames'] = [{'index': i, 'layers': {n: asset for n in ('slabs', 'piles', 'boundaries')}} for i in range(51)]
                (folder/'catalogue.json').write_text(json.dumps(doc))
                (folder/'mesh.bin').write_bytes(b'wrong')
                with self.assertRaisesRegex(ValueError, 'differs from catalogue'):
                    pack_experiments(root/'stage', [])
