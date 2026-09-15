import copy
import json
from unittest.mock import patch
from django.conf import settings
from django.test import SimpleTestCase
from core.mantle import globe_overlay


class OverlayConfigTests(SimpleTestCase):
    def setUp(self):
        self.config = json.loads((settings.BASE_DIR/'annotations/mantle-overlay.json').read_text())
        self.data = {'source_archive_sha256': self.config['source_archive_sha256'], 'frames':[
            {'age_ma':f['age_ma'], 'layers':{name:{'points':3,'indices':3,'bytes':48,'primitive':'triangles',
             'sha256':digest,'file':f'{name}-46-{digest[:16]}.bin'} for name,digest in f['layers_sha256'].items()}}
            for f in self.config['frames']]}

    def test_only_audited_age_and_source_pair_is_exposed(self):
        with patch('core.mantle.catalogue',return_value=self.data):
            result=globe_overlay()
        self.assertEqual([f['age_ma'] for f in result['frames']],[80,60,40,20,0])
        self.assertEqual(result['frames'][0]['rotation_matrix'],self.config['frames'][0]['rotation_matrix'])
        self.assertEqual(set(result['frames'][0]['layers']),{'slabs','piles'})
        for broken in [None, {**self.data,'source_archive_sha256':'wrong'}, {**self.data,'frames':[]}, {**self.data,'frames':self.data['frames'][:-1]}]:
            with self.subTest(broken=broken), patch('core.mantle.catalogue',return_value=broken):
                self.assertIsNone(globe_overlay())
        altered=copy.deepcopy(self.data)
        altered['frames'][0]['layers']['slabs']['sha256']='wrong'
        with patch('core.mantle.catalogue',return_value=altered):self.assertIsNone(globe_overlay())

    def test_english_overlay_strings(self):
        with patch('core.mantle.catalogue',return_value=self.data), self.settings(LANGUAGE_CODE='en'):
            from django.utils.translation import override
            with override('en'):
                self.assertNotRegex(json.dumps(globe_overlay(),ensure_ascii=False),'[가-힣]')
