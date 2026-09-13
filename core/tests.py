from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db import OperationalError
from django.test import RequestFactory, TestCase, override_settings

from config.version import VERSION
from core import globe as globe_module


@override_settings(GLOBE_SERIES='scotese')
class SiteTests(TestCase):
    def test_public_pages(self):
        for url in ["/", "/about/", "/privacy/", "/contact/"]:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, "EarthThruTime3D")
                self.assertContains(response, f"v{VERSION}")
                self.assertContains(response, "PaleoBytes")

    def test_health_status_and_sentinel(self):
        with TemporaryDirectory() as directory:
            sentinel = Path(directory) / "INTEGRITY_FAIL"
            with self.settings(INTEGRITY_SENTINEL=sentinel):
                response = self.client.get("/healthz")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["status"], "ok")
                self.assertEqual(response.json()["version"], VERSION)
                sentinel.touch()
                response = self.client.get("/healthz")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["status"], "degraded")

    def test_database_failure_is_unhealthy_without_error_leak(self):
        with patch("core.views.connection.cursor", side_effect=OperationalError("private DB path")):
            with self.assertLogs("core.views", level="ERROR"):
                response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["status"], "unhealthy")
        self.assertNotIn("private DB path", response.content.decode())

    def test_admin_requires_superuser(self):
        request = RequestFactory().get("/admin/")
        request.user = get_user_model()(is_active=True, is_staff=True, is_superuser=False)
        self.assertFalse(admin.site.has_permission(request))

        request.user.is_superuser = True
        self.assertTrue(admin.site.has_permission(request))
        request.user.is_active = False
        self.assertFalse(admin.site.has_permission(request))


@override_settings(GLOBE_SERIES='scotese')
class GlobeTests(TestCase):
    def test_all_frames_have_calibration_and_local_routes(self):
        with self.settings(SCOTESE_VIEWER_ENABLED=True):
            response = self.client.get('/')
        frames = response.context['frames']
        self.assertEqual(len(frames), 17)
        self.assertEqual(frames[5]['age'], 356)
        self.assertEqual(frames[13]['age'], 50.2)
        for frame in frames:
            self.assertTrue(frame['url'].startswith('/globe/maps/'))
            self.assertEqual(len(frame['bounds']), 4)

    def test_map_endpoint_is_allowlisted_and_disabled_when_viewer_is_off(self):
        with self.settings(SCOTESE_VIEWER_ENABLED=False):
            self.assertEqual(self.client.get('/globe/maps/scotese-000.jpg').status_code, 404)
            self.assertEqual(self.client.get('/').context['frames'], [])
        with self.settings(SCOTESE_VIEWER_ENABLED=True):
            self.assertEqual(self.client.get('/globe/maps/unknown.jpg').status_code, 404)

    def test_field_endpoint_follows_the_same_allowlist(self):
        with self.settings(SCOTESE_VIEWER_ENABLED=False):
            self.assertEqual(self.client.get('/globe/fields/scotese-000.png').status_code, 404)
        with self.settings(SCOTESE_VIEWER_ENABLED=True):
            self.assertEqual(self.client.get('/globe/fields/unknown.png').status_code, 404)

    def test_frames_offer_a_field_only_when_one_has_been_generated(self):
        with self.settings(SCOTESE_VIEWER_ENABLED=True):
            response = self.client.get('/')
            frames = response.context['frames']
            for frame in frames:
                if frame["field"] is not None:
                    self.assertTrue(frame["field"].startswith('/globe/fields/'))
            self.assertEqual(response.context['fields_available'],
                             any(frame["field"] for frame in frames))
            with patch('core.globe.field_path') as path:
                path.return_value.exists.return_value = False
                response = self.client.get('/')
            self.assertFalse(response.context['fields_available'])
            self.assertNotContains(response, 'id="surface"')

    def test_missing_field_returns_404(self):
        with self.settings(SCOTESE_VIEWER_ENABLED=True):
            with patch('core.globe.field_path') as path:
                path.return_value.open.side_effect = FileNotFoundError
                self.assertEqual(self.client.get('/globe/fields/scotese-000.png').status_code, 404)

    def test_frames_carry_named_landmass_points(self):
        with self.settings(SCOTESE_VIEWER_ENABLED=True):
            frames = self.client.get('/').context['frames']
        named = {frame['id']: [name['name'] for name in frame['names']] for frame in frames}
        if not any(named.values()):
            self.skipTest('segmentation has not been run in this checkout')
        self.assertIn('아프리카', named['scotese-000'])
        self.assertIn('판게아', named['scotese-237'])
        for frame in frames:
            for name in frame['names']:
                self.assertTrue(-180 <= name['lon'] <= 180)
                self.assertTrue(-90 <= name['lat'] <= 90)

    def test_names_are_empty_when_the_report_is_missing(self):
        with self.settings(SCOTESE_VIEWER_ENABLED=True):
            with patch('core.globe.derived_path') as path:
                path.return_value.exists.return_value = False
                frames = self.client.get('/').context['frames']
        self.assertEqual([frame['names'] for frame in frames], [[]] * len(frames))

    def test_sampling_falls_back_when_asked_for_something_unlisted(self):
        request = RequestFactory().get('/', {'steps': '999'})
        self.assertEqual(globe_module.sampling(request), {'interval_ma': None, 'steps': 4})
        request = RequestFactory().get('/', {'steps': '16'})
        self.assertEqual(globe_module.sampling(request), {'interval_ma': None, 'steps': 16})
        request = RequestFactory().get('/', {'interval': '1'})
        self.assertEqual(globe_module.sampling(request), {'interval_ma': 1.0, 'steps': None})
        request = RequestFactory().get('/', {'interval': 'abc', 'steps': '8'})
        self.assertEqual(globe_module.sampling(request), {'interval_ma': None, 'steps': 8})
        with self.settings(SCOTESE_VIEWER_STEPS='2'):
            self.assertEqual(globe_module.sampling()['steps'], 2)
        with self.settings(SCOTESE_VIEWER_INTERVAL_MA='5'):
            self.assertEqual(globe_module.sampling()['interval_ma'], 5.0)

    def test_timeline_keeps_every_source_map_as_its_own_stop(self):
        frames = [{'age': age} for age in [650, 514, 66, 14, 0.018, 0]]
        for plan in [{'interval_ma': None, 'steps': 1}, {'interval_ma': None, 'steps': 8},
                     {'interval_ma': 1.0, 'steps': None}, {'interval_ma': 25.0, 'steps': None}]:
            stops = globe_module.timeline(frames, plan)
            with self.subTest(plan=plan):
                ages = [stop[3] for stop in stops]
                self.assertEqual(ages, sorted(ages, reverse=True))
                self.assertEqual(stops[0][2], 0.0)
                self.assertEqual(stops[-1][2], 0.0)
                observed = {stop[3] for stop in stops if stop[2] == 0.0}
                for frame in frames:
                    self.assertIn(frame['age'], observed)
                for older, newer, blend, age in stops:
                    self.assertTrue(0.0 <= blend < 1.0)
                    self.assertTrue(frames[newer]['age'] <= age <= frames[older]['age'])

    def test_timeline_step_count_follows_the_plan(self):
        frames = [{'age': age} for age in [100, 50, 0]]
        self.assertEqual(len(globe_module.timeline(frames, {'interval_ma': None, 'steps': 1})), 3)
        self.assertEqual(len(globe_module.timeline(frames, {'interval_ma': None, 'steps': 4})), 9)
        self.assertEqual(len(globe_module.timeline(frames, {'interval_ma': 10.0, 'steps': None})), 11)
        self.assertEqual(globe_module.timeline([{'age': 7}], {'interval_ma': None, 'steps': 4}),
                         [[0, 0, 0.0, 7]])

    def test_a_track_carries_identity_across_a_rename(self):
        frames = [{"id": "a", "age": 100.0}, {"id": "b", "age": 50.0}]
        pieces = {"a": [{"names": [{"name": "아시아", "track": "eurasia"}],
                         "centroid": [80, 40], "radius_deg": 30.0, "area_px": 9000}],
                  "b": [{"names": [{"name": "유라시아", "track": "eurasia"}],
                         "centroid": [85, 45], "radius_deg": 30.0, "area_px": 9500}]}
        self.assertEqual(len(globe_module.motions(frames, pieces)[0]), 1)
        for side in pieces.values():
            side[0]["names"][0].pop("track")
        self.assertEqual(globe_module.motions(frames, pieces)[0], [])

    def test_motion_pairs_only_where_a_piece_keeps_its_identity(self):
        def piece(name, lon, lat, radius=20.0, area=1000):
            return {"names": [{"name": name}], "centroid": [lon, lat],
                    "radius_deg": radius, "area_px": area}

        frames = [{"id": "a", "age": 100.0}, {"id": "b", "age": 50.0}]
        pieces = {"a": [piece("대륙", 0, 0)], "b": [piece("대륙", 10, 0)]}
        gap = globe_module.motions(frames, pieces)[0]
        self.assertEqual(len(gap), 1)
        self.assertAlmostEqual(gap[0]["moved"], 10.0, places=3)
        self.assertEqual(gap[0]["lon"], 0)
        self.assertEqual(gap[0]["to_lon"], 10)

        # A piece that splits has no single place to travel to.
        pieces = {"a": [{"names": [{"name": "북"}, {"name": "남"}], "centroid": [0, 0],
                         "radius_deg": 20.0, "area_px": 1000}],
                  "b": [piece("북", 20, 20), piece("남", -20, -20)]}
        self.assertEqual(globe_module.motions(frames, pieces)[0], [])

        # A shared name is kept however fast the implied motion is, because India
        # really did cross the Tethys at close to two degrees of arc per million years.
        # The rate is reported so an implausible pairing stays visible.
        fast = [{"id": "a", "age": 60.0}, {"id": "b", "age": 50.0}]
        pieces = {"a": [piece("인도", 0, 0)], "b": [piece("인도", 18, 0)]}
        pair = globe_module.motions(fast, pieces)[0][0]
        self.assertAlmostEqual(pair["deg_per_ma"], 1.8, places=3)
        self.assertFalse(pair["fast"])
        pieces = {"a": [piece("대륙", 0, 0)], "b": [piece("대륙", 40, 0)]}
        pair = globe_module.motions(fast, pieces)[0][0]
        self.assertTrue(pair["fast"])

        # Two pieces whose mapped areas differ this much are different extents of the
        # same landmass, so their centroids cannot be compared.
        pieces = {"a": [piece("남극", 0, -70, area=8000)],
                  "b": [piece("남극", 25, -70, area=2000)]}
        self.assertEqual(globe_module.motions(frames, pieces)[0], [])

        # Islands are too small to carry a continent's morph.
        pieces = {"a": [piece("섬", 0, 0, radius=1.0)], "b": [piece("섬", 5, 0, radius=1.0)]}
        self.assertEqual(globe_module.motions(frames, pieces)[0], [])

    def test_motion_pairs_are_capped_and_ordered_by_size(self):
        frames = [{"id": "a", "age": 400.0}, {"id": "b", "age": 0.0}]
        pieces = {"a": [], "b": []}
        for index in range(globe_module.MAX_MOTIONS + 4):
            radius = 5.0 + index
            pieces["a"].append({"names": [{"name": str(index)}], "centroid": [0, 0],
                                "radius_deg": radius, "area_px": 1000})
            pieces["b"].append({"names": [{"name": str(index)}], "centroid": [1, 0],
                                "radius_deg": radius, "area_px": 1000})
        gap = globe_module.motions(frames, pieces)[0]
        self.assertEqual(len(gap), globe_module.MAX_MOTIONS)
        self.assertEqual([pair["radius"] for pair in gap],
                         sorted((pair["radius"] for pair in gap), reverse=True))

    def test_separation_measures_along_the_globe(self):
        self.assertAlmostEqual(globe_module.separation([0, 0], [0, 0]), 0.0, places=6)
        self.assertAlmostEqual(globe_module.separation([0, 0], [90, 0]), 90.0, places=4)
        self.assertAlmostEqual(globe_module.separation([0, 89], [180, 89]), 2.0, places=4)

    def test_source_maps_stay_off_the_network_until_they_are_published(self):
        with self.settings(SCOTESE_VIEWER_ENABLED=True, SCOTESE_SOURCE_MAPS_PUBLIC=False):
            response = self.client.get('/')
            self.assertEqual(self.client.get('/globe/maps/scotese-000.jpg').status_code, 404)
            self.assertFalse(response.context['source_maps_public'])
            self.assertEqual({frame['url'] for frame in response.context['frames']}, {None})
            self.assertNotContains(response, 'id="surface"')
            self.assertNotContains(response, 'id="source-preview"')
            self.assertContains(response, 'scotese.com')
        with self.settings(SCOTESE_VIEWER_ENABLED=True, SCOTESE_SOURCE_MAPS_PUBLIC=True):
            response = self.client.get('/')
            self.assertTrue(response.context['source_maps_public'])
            self.assertTrue(all(frame['url'] for frame in response.context['frames']))

    def test_health_fails_when_the_runtime_bundle_is_missing(self):
        with self.settings(SCOTESE_VIEWER_ENABLED=True, SCOTESE_DERIVED_DIR='/nonexistent'):
            response = self.client.get('/healthz')
        self.assertEqual(response.status_code, 503)
        body = response.json()
        self.assertEqual(body['status'], 'unhealthy')
        self.assertEqual(body['fields']['missing'], body['fields']['expected'])
        with self.settings(SCOTESE_VIEWER_ENABLED=False, SCOTESE_DERIVED_DIR='/nonexistent'):
            response = self.client.get('/healthz')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['fields']['required'])

    def test_missing_map_returns_404(self):
        with self.settings(SCOTESE_VIEWER_ENABLED=True):
            with patch('pathlib.Path.open', side_effect=FileNotFoundError):
                with patch('core.globe.catalogue', return_value={'maps': [{'id': 'test', 'image': {'path': 'missing.jpg'}}]}):
                    self.assertEqual(self.client.get('/globe/maps/test.jpg').status_code, 404)


@override_settings(SCOTESE_VIEWER_ENABLED=True, GLOBE_SERIES='paleodem')
class PaleodemTests(TestCase):
    """The elevation series: 109 grids served through the same field route."""

    def setUp(self):
        self.derived = TemporaryDirectory()
        self.addCleanup(self.derived.cleanup)
        settings_patch = self.settings(SCOTESE_DERIVED_DIR=self.derived.name)
        settings_patch.enable()
        self.addCleanup(settings_patch.disable)

    def build(self, item):
        globe_module.field_path(item).write_bytes(b'png')

    def test_catalogue_is_oldest_first_with_unique_slug_ids(self):
        items = globe_module.paleodem_items()
        self.assertEqual(len(items), 109)
        self.assertEqual([items[0]['age_ma'], items[-1]['age_ma']], [540, 0])
        self.assertEqual(len({item['id'] for item in items}), 109)
        for item in items:
            self.assertRegex(item['id'], r'^paleodem-\d{4}$')

    def test_falls_back_to_scotese_until_every_field_is_built(self):
        self.assertEqual(globe_module.series(RequestFactory().get('/')), 'scotese')
        response = self.client.get('/')
        self.assertEqual(response.context['series'], 'scotese')
        items = globe_module.elevation_timeline()
        for item in items[1:]:
            self.build(item)
        self.assertEqual(globe_module.series(RequestFactory().get('/')), 'scotese',
                         'the 650 Ma prelude counts: a partial build has frames that cannot render')
        self.build(items[0])
        self.assertEqual(globe_module.series(RequestFactory().get('/')), 'paleodem')
        self.assertEqual(globe_module.series(RequestFactory().get('/?series=scotese')), 'scotese')
        self.assertEqual(globe_module.series(RequestFactory().get('/?series=nope')), 'paleodem')

    def test_frames_carry_relief_and_no_source_map(self):
        for item in globe_module.elevation_timeline():
            self.build(item)
        response = self.client.get('/')
        frames = response.context['frames']
        self.assertEqual(len(frames), 110)
        self.assertEqual(response.context['series'], 'paleodem')
        self.assertEqual((frames[0]['id'], frames[0]['relief'], frames[0]['age']), ('scotese-650', False, 650))
        self.assertIn('분할 마스크', frames[0]['label'])
        self.assertTrue(all(frame['relief'] for frame in frames[1:]))
        self.assertTrue(all(frame['url'] is None for frame in frames))
        self.assertTrue(all(frame['label'] and frame['label'] != frame['title'] for frame in frames),
                        'labels are Korean, titles the source stage names')
        self.assertTrue(all(frame['field'] == f"/globe/fields/{frame['id']}.png" for frame in frames))
        self.assertEqual([stop for stop in response.context['stops'] if stop[2] == 0].__len__(), 110)
        self.assertEqual(response.context['motions'], [[] for _ in range(109)])
        self.assertContains(response, 'id="surface"')
        self.assertContains(response, 'zenodo.org/records/5460860')
        self.assertNotContains(response, 'source-preview')

    def test_health_validates_the_series_actually_served(self):
        report = self.client.get('/healthz').json()
        self.assertEqual((report['fields']['series'], report['fields']['expected']), ('scotese', 17))
        for item in globe_module.elevation_timeline():
            self.build(item)
        response = self.client.get('/healthz')
        report = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual((report['fields']['series'], report['fields']['expected'],
                          report['fields']['missing']), ('paleodem', 110, 0))

    def test_field_route_serves_a_paleodem_slice(self):
        item = globe_module.paleodem_items()[-1]
        self.assertEqual(self.client.get(f"/globe/fields/{item['id']}.png").status_code, 404)
        self.build(item)
        response = self.client.get(f"/globe/fields/{item['id']}.png")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/png')
        self.assertEqual(self.client.get(f"/globe/maps/{item['id']}.jpg").status_code, 404)
