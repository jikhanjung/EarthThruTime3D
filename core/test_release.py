import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import SimpleTestCase

from deploy.host.update_compose_env import updated
from deploy.pack_data import pack_experiments
from deploy.pack_data import verified_experiment_path


class ReleaseTests(SimpleTestCase):
    def test_unsafe_section_path_is_rejected_before_reading(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'assets'
            source.mkdir()
            outside = root / 'outside.json'
            outside.write_bytes(b'not even JSON')
            record = {'file': '../outside.json', 'bytes': outside.stat().st_size,
                      'sha256': hashlib.sha256(outside.read_bytes()).hexdigest()}
            with self.assertRaisesRegex(ValueError, 'Unsafe'):
                verified_experiment_path(source, record)

    def test_smoke_uses_compose_effective_port_and_does_not_execute_env(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copy('deploy/host/smoke.sh', root/'smoke.sh')
            (root/'.env').write_text('HOST_PORT=8999\nUNUSED=$(touch should-not-exist)\n')
            # Compose is responsible for .env/shell interpolation. Smoke consumes
            # only its resolved published port, never assumes the default 8014.
            (root/'docker').write_text('#!/bin/sh\ncat <<\'JSON\'\n'
                '{"services":{"earththrutime3d":{"ports":[{"target":8000,"published":"8999"}]}}}\nJSON\n')
            (root/'curl').write_text('#!/bin/sh\nprintf "%s" "$2" > requested-url\ncat <<\'JSON\'\n'
                '{"status":"ok","version":"0.12.0","fields":{"required":true,"missing":0,"expected":90}}\nJSON\n')
            for name in ['docker', 'curl']:
                (root/name).chmod(0o755)
            env = dict(os.environ, PATH=str(root) + os.pathsep + os.environ['PATH'])
            result = subprocess.run(['bash', str(root/'smoke.sh'), '0.12.0'],
                                    env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((root/'requested-url').read_text(), 'http://127.0.0.1:8999/healthz')
            self.assertFalse((root/'should-not-exist').exists())

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
