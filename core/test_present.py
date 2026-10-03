import hashlib
import json
from pathlib import Path
import tempfile
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from core.present import globe_config, status
from deploy.pack_data import pack_present


def asset(root, key, extension, blob):
    digest = hashlib.sha256(blob).hexdigest()
    name = f'{key}-{digest[:12]}.{extension}'
    (root / name).write_bytes(blob)
    return {'file': name, 'bytes': len(blob), 'sha256': digest}


class PresentEarthTests(SimpleTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.override = override_settings(PRESENT_DERIVED_DIR=self.root, SCOTESE_VIEWER_ENABLED=True)
        self.override.enable()
        self.addCleanup(self.override.disable)
        wind = {'u': [-10.0, 12.5], 'v': [-8.0, 9.0]}
        self.data = {
            'schema_version': 1,
            'base': {'layer': 'BlueMarble_ShadedRelief_Bathymetry', 'citation': 'NASA', 'imagery_epoch': '2004 composite',
                     'assets': {'4096': asset(self.root, '4096', 'jpg', b'small'),
                                '8192': asset(self.root, '8192', 'jpg', b'large')}},
            'weather': {'t': '2026-10-01T18:00Z',
                        'wind': {'levels': ['10m', '250hPa'], 'width': 1440, 'height': 721, '10m': wind, '250hPa': wind},
                        'clouds': {'model': {'width': 1440, 'height': 721},
                                   'sat': {'width': 1800, 'height': 900, 'limit_deg': 72.7}},
                        'credits': {'gfs': 'NOAA GFS', 'gmgsi': 'NOAA GMGSI'},
                        'assets': {key: asset(self.root, key, 'png', key.encode())
                                   for key in ('10m', '250hPa', 'cloud-model', 'cloud-sat')}},
            'ocean': {'width': 1440, 'height': 720, 'depth_m': 5, 'days': 3, 'period': ['1992', '2018'],
                      'samples': 324, 'u': [-1.0, 1.5], 'v': [-1.2, 1.4], 'citation': 'ECCO2',
                      'assets': {'mean': asset(self.root, 'mean', 'png', b'ocean')}},
        }
        self.save()

    def save(self):
        (self.root / 'catalogue.json').write_text(json.dumps(self.data))

    def test_config_names_every_section_and_its_moment(self):
        config = globe_config()
        self.assertEqual(set(config), {'base', 'weather', 'ocean'})
        self.assertEqual(config['weather']['t'], '2026-10-01T18:00Z')
        self.assertEqual(config['weather']['wind']['10m']['u'], [-10.0, 12.5])
        self.assertTrue(config['weather']['clouds']['sat'].startswith('/present/assets/cloud-sat-'))
        self.assertEqual(config['ocean']['period'], ['1992', '2018'])

    def test_assets_are_verified_and_immutable(self):
        item = self.data['weather']['assets']['10m']
        response = self.client.get(f"/present/assets/{item['file']}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/png')
        self.assertIn('immutable', response['Cache-Control'])
        self.assertEqual(self.client.get(f"/present/assets/{self.data['base']['assets']['4096']['file']}")['Content-Type'],
                         'image/jpeg')
        (self.root / item['file']).write_bytes(b'1xm')     # same size, other bytes
        self.assertEqual(self.client.get(f"/present/assets/{item['file']}").status_code, 404)
        self.assertEqual(self.client.get('/present/assets/catalogue.json').status_code, 404)

    def test_a_bad_section_hides_only_itself(self):
        self.data['weather']['t'] = 'yesterday'
        self.save()
        self.assertEqual(set(globe_config()), {'base', 'ocean'})
        self.data['ocean']['assets']['mean']['file'] = '../mean.png'
        self.save()
        self.assertEqual(set(globe_config()), {'base'})
        (self.root / self.data['base']['assets']['8192']['file']).unlink()
        self.assertIsNone(globe_config())

    def test_disabled_or_missing(self):
        with override_settings(SCOTESE_VIEWER_ENABLED=False):
            self.assertIsNone(globe_config())
        (self.root / 'catalogue.json').unlink()
        self.assertIsNone(globe_config())

    def test_page_offers_the_controls_and_says_it_is_not_live(self):
        response = self.client.get('/?masks=paleodem2018')
        self.assertEqual(response.status_code, 200)
        page = response.content.decode()
        for marker in ('id="satellite"', 'id="wind-layer"', 'id="currents"', 'id="cloud-layer"',
                       'id="flux-when"', 'id="globe-present"', 'core/flux.js'):
            self.assertIn(marker, page)
        self.assertIn('실시간이 아닙니다', page)
        english = self.client.get('/?masks=paleodem2018', HTTP_COOKIE='django_language=en')
        self.assertNotIn('실시간이 아닙니다', english.content.decode())

    def test_page_without_data_has_no_controls(self):
        (self.root / 'catalogue.json').unlink()
        page = self.client.get('/?masks=paleodem2018').content.decode()
        self.assertNotIn('id="wind-layer"', page)
        self.assertNotIn('id="satellite"', page)

    def test_release_packs_only_catalogued_files(self):
        project = self.root / 'project'
        derived = project / 'data/derived/present-earth'
        derived.mkdir(parents=True)
        for path in self.root.iterdir():
            if path.is_file():
                (derived / path.name).write_bytes(path.read_bytes())
        (derived / 'gfs.grib2').write_bytes(b'raw')
        files = []
        with patch('deploy.pack_data.BASE_DIR', project):
            pack_present(project / 'stage', files)
            self.assertEqual(len(files), 1 + 2 + 4 + 1)
            self.assertFalse((project / 'stage/present-earth/gfs.grib2').exists())
            (derived / self.data['ocean']['assets']['mean']['file']).write_bytes(b'tampered')
            with self.assertRaises(ValueError):
                pack_present(project / 'stage2', [])


class LivePresentWeatherTests(SimpleTestCase):
    """The daily moment the host's cron writes (jikhanjung P11)."""

    save = PresentEarthTests.save

    def setUp(self):
        PresentEarthTests.setUp(self)
        # The release's moment, older than the daily one written below
        self.data['weather']['t'] = (datetime.now(timezone.utc) - timedelta(hours=30)).strftime('%Y-%m-%dT%H:00Z')
        self.save()
        self.live_temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.live_temp.cleanup)
        self.live = Path(self.live_temp.name)
        self.live_override = override_settings(PRESENT_LIVE_DIR=str(self.live))
        self.live_override.enable()
        self.addCleanup(self.live_override.disable)
        self.write_live(datetime.now(timezone.utc) - timedelta(hours=10))

    def write_live(self, when, previous=True):
        weather = json.loads(json.dumps(self.data['weather']))
        weather['t'] = when.strftime('%Y-%m-%dT%H:00Z')
        weather['assets'] = {key: asset(self.live, key, 'png', f'live {key} {when}'.encode())
                             for key in ('10m', '250hPa', 'cloud-model', 'cloud-sat')}
        if previous:
            weather['previous'] = {'assets': {key: asset(self.live, key, 'png', f'old {key}'.encode())
                                              for key in ('10m', '250hPa', 'cloud-model', 'cloud-sat')}}
        (self.live / 'catalogue.json').write_text(json.dumps({'schema_version': 1, 'weather': weather}))
        (self.live / 'status.json').write_text(json.dumps({'at': 'x', 'result': 'ok', 't': weather['t'], 'last_ok': 'x'}))
        self.live_weather = weather

    def test_a_fresh_daily_moment_replaces_the_release_one(self):
        config = globe_config()['weather']
        self.assertEqual(config['source'], 'live')
        self.assertEqual(config['t'], self.live_weather['t'])
        live_file = self.live_weather['assets']['10m']['file']
        self.assertIn(live_file, config['wind']['10m']['url'])
        self.assertEqual(self.client.get(f'/present/assets/{live_file}').status_code, 200)
        # The moment before stays servable for a page opened just before the swap
        old = self.live_weather['previous']['assets']['cloud-sat']['file']
        self.assertEqual(self.client.get(f'/present/assets/{old}').status_code, 200)
        # Base and currents still come from the release
        base = self.data['base']['assets']['4096']['file']
        self.assertEqual(self.client.get(f'/present/assets/{base}').status_code, 200)
        health = status()
        self.assertEqual(health['source'], 'live')
        self.assertEqual(health['refresh']['result'], 'ok')

    def test_an_old_or_broken_moment_falls_back_to_the_release(self):
        self.write_live(datetime.now(timezone.utc) - timedelta(hours=49))
        self.assertEqual(globe_config()['weather']['source'], 'release')
        self.write_live(datetime.now(timezone.utc) - timedelta(hours=1))
        (self.live / self.live_weather['assets']['250hPa']['file']).unlink()
        self.assertEqual(globe_config()['weather']['source'], 'release')
        (self.live / 'catalogue.json').write_text('{broken')
        self.assertEqual(globe_config()['weather']['source'], 'release')
        self.assertEqual(status()['source'], 'release')

    def test_a_moment_not_newer_than_the_release_is_ignored(self):
        self.write_live(datetime.now(timezone.utc) - timedelta(hours=40))
        self.assertEqual(globe_config()['weather']['source'], 'release')

    def test_the_page_says_the_moment_is_daily(self):
        page = self.client.get('/?masks=paleodem2018').content.decode()
        self.assertIn('하루 한 번', page)
        english = self.client.get('/?masks=paleodem2018', HTTP_COOKIE='django_language=en').content.decode()
        self.assertIn('fetched once a day', english)
