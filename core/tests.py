from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.conf import settings
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db import OperationalError
from django.test import RequestFactory, TestCase

from config.version import VERSION
from core import globe as globe_module


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


class GlobeTests(TestCase):
    def test_the_2016_atlas_is_the_default_mask_source(self):
        with self.settings(SCOTESE_VIEWER_ENABLED=True, SCOTESE_SOURCE_MAPS_PUBLIC=True):
            response = self.client.get('/')
        frames = response.context['frames']
        self.assertEqual(response.context['mask']['id'], 'paleoatlas2016')
        self.assertEqual(len(frames), 90)
        self.assertEqual(frames[0]['age'], 750.0)
        self.assertEqual(frames[-1]['id'], 'paleoatlas-000')
        ages = [frame['age'] for frame in frames]
        self.assertEqual(ages, sorted(ages, reverse=True))
        for frame in frames:
            # The 2016 rasters are never offered, even where the 2002 maps are public.
            self.assertIsNone(frame['url'])
            self.assertIsNone(frame['bounds'])
            self.assertTrue(frame['label'])
        self.assertFalse(response.context['source_maps_public'])
        self.assertNotContains(response, 'id="surface"')
        self.assertContains(response, '?masks=scotese2002')
        self.assertEqual(self.client.get('/globe/maps/paleoatlas-000.jpg').status_code, 404)

    def test_the_mask_source_can_be_switched_for_comparison_and_falls_back(self):
        for asked, expected in (('scotese2002', 'scotese2002'), ('bogus', 'paleoatlas2016'),
                                (None, 'paleoatlas2016')):
            request = RequestFactory().get('/', {'masks': asked} if asked else {})
            self.assertEqual(globe_module.mask_source(request), expected)
        with self.settings(MASK_SOURCE='scotese2002'):
            self.assertEqual(globe_module.mask_source(), 'scotese2002')
        with self.settings(MASK_SOURCE='nonsense'):
            self.assertEqual(globe_module.mask_source(), 'paleoatlas2016')

    def test_period_labels_follow_the_age_not_the_file_name(self):
        label = globe_module.period_label
        self.assertEqual(label({'id': 'paleoatlas-000', 'age_ma': 0.0}), '현재')
        self.assertEqual(label({'id': 'paleoatlas-lgm', 'age_ma': 0.021}), '최후빙기 최성기')
        self.assertEqual(label({'id': 'paleoatlas-120', 'age_ma': 120.0}), '전기 백악기')
        self.assertEqual(label({'id': 'paleoatlas-255', 'age_ma': 255.0}), '후기 페름기')
        self.assertEqual(label({'id': 'paleoatlas-600', 'age_ma': 600.0}), '에디아카라기')
        self.assertEqual(label({'id': 'paleoatlas-750', 'age_ma': 750.0}), '토니아기')

    def test_atlas_frames_carry_plate_names_and_rotation_motions(self):
        with self.settings(SCOTESE_VIEWER_ENABLED=True):
            response = self.client.get('/')
        frames = response.context['frames']
        motions = response.context['motions']
        if not motions:
            self.skipTest('atlas motions have not been computed in this checkout')
        self.assertEqual(len(motions), len(frames) - 1)
        named = {frame['id']: {name['name'] for name in frame['names']} for frame in frames}
        self.assertIn('아프리카', named['paleoatlas-000'])
        self.assertIn('로렌시아', named['paleoatlas-420'])
        for gap in motions:
            self.assertLessEqual(len(gap), globe_module.MAX_MOTIONS)
            for pair in gap:
                for key in ('lon', 'lat', 'to_lon', 'to_lat', 'radius'):
                    self.assertIn(key, pair)

    def test_atlas_motions_that_do_not_match_the_frames_are_ignored(self):
        frames = [{'id': 'a'}, {'id': 'b'}, {'id': 'c'}]
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'motions.json'
            with self.settings(PALEOATLAS_DERIVED_DIR=directory):
                self.assertEqual(globe_module.atlas_motions(frames), [])
                path.write_text('{"gaps": [{"from": "a", "to": "b", "pairs": [{"lon": 1}]}]}')
                self.assertEqual(globe_module.atlas_motions(frames), [])
                path.write_text('{"gaps": [{"from": "a", "to": "b", "pairs": [{"lon": 1}]},'
                                ' {"from": "b", "to": "c", "pairs": []}]}')
                self.assertEqual(globe_module.atlas_motions(frames), [[{"lon": 1}], []])

    def test_fossil_coastlines_are_offered_over_the_atlas_only(self):
        with self.settings(SCOTESE_VIEWER_ENABLED=True):
            response = self.client.get('/')
            layer = response.context['coastlines']
            if layer is None:
                self.skipTest('PaleoCoastlines have not been packed in this checkout')
            self.assertEqual(len(layer['ages']), 81)
            self.assertContains(response, 'id="coastline"')
            self.assertIsNone(self.client.get('/', {'masks': 'scotese2002'}).context['coastlines'])
            served = self.client.get('/globe/coastlines/255.json')
            self.assertEqual(served.status_code, 200)
            body = b''.join(served.streaming_content)
            self.assertIn(b'"rings"', body)
            self.assertEqual(self.client.get('/globe/coastlines/3.json').status_code, 404)
        with self.settings(SCOTESE_VIEWER_ENABLED=False):
            self.assertEqual(self.client.get('/globe/coastlines/0.json').status_code, 404)

    def test_the_timeline_offers_a_one_million_year_spacing(self):
        with self.settings(SCOTESE_VIEWER_ENABLED=True):
            response = self.client.get('/', {'interval': '1'})
        self.assertEqual(response.context['sampling_choice'], 'interval:1')
        self.assertContains(response, '<option value="interval:1" selected>1 Myr</option>', html=False)
        mapped = [stop[3] for stop in response.context['stops'] if stop[0] >= 0]
        gaps = [older - newer for older, newer in zip(mapped, mapped[1:])]
        self.assertLessEqual(max(gaps), 1.0 + 1e-6)
        with self.settings(SCOTESE_VIEWER_ENABLED=True):
            default = self.client.get('/')
        self.assertEqual(default.context['sampling_choice'], 'steps:4')

    def test_the_header_is_one_line_without_a_menu_or_tag(self):
        with self.settings(SCOTESE_VIEWER_ENABLED=True):
            response = self.client.get('/')
        self.assertContains(response, 'class="page-title"')
        self.assertNotContains(response, '3D 고지리 탐색')
        self.assertNotContains(response, 'EARTH THROUGH TIME')
        self.assertNotContains(response, 'aria-label="주 메뉴"')
        self.assertIn('periods', response.context)
        self.assertEqual(globe_module.period_label({'id': 'x', 'age_ma': 252.5}), '후기 페름기')

    def test_english_pages_carry_no_korean_and_english_names(self):
        # The language switch sets a cookie; every page must then render without any
        # untranslated Korean, and the viewer's data must carry English continent names.
        response = self.client.get('/lang/en/', {'next': '/about/'})
        self.assertEqual(response['Location'], '/about/')
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = 'en'
        # With a key configured the locked model is listed too, and its menu title must
        # translate like everything else.
        with self.settings(SCOTESE_VIEWER_ENABLED=True, ACCESS_KEY="a-key-for-the-test"):
            for url in ('/', '/?masks=scotese2002', '/about/', '/privacy/', '/contact/'):
                with self.subTest(url=url):
                    page = self.client.get(url)
                    self.assertEqual(page.status_code, 200)
                    self.assertNotRegex(page.content.decode(), '[가-힣]')
            home = self.client.get('/')
        self.assertContains(home, '<html lang="en">')
        self.assertContains(home, 'aria-current="true">EN</a>')
        frames = home.context['frames']
        self.assertEqual(frames[0]['label'], 'Tonian')
        names = {name['name'] for name in frames[-1]['names']}
        if names:
            self.assertIn('Africa', names)
        self.assertEqual(home.context['strings']['present'], 'Present')
        self.assertEqual(home.context['mask']['title'], 'PALEOMAP PaleoAtlas (2016)')
        self.assertEqual(self.client.get('/lang/xx/').status_code, 404)
        self.assertEqual(self.client.get('/lang/ko/', {'next': 'https://evil.example/'})['Location'], '/')

    def test_korean_stays_the_default(self):
        with self.settings(SCOTESE_VIEWER_ENABLED=True):
            home = self.client.get('/')
        self.assertContains(home, '<html lang="ko">')
        self.assertContains(home, 'aria-current="true">KO</a>')
        self.assertEqual(home.context['frames'][0]['label'], '토니아기')

    def test_atlas_fields_are_served_by_id(self):
        with self.settings(SCOTESE_VIEWER_ENABLED=False):
            self.assertEqual(self.client.get('/globe/fields/paleoatlas-000.png').status_code, 404)
        with self.settings(SCOTESE_VIEWER_ENABLED=True):
            if not globe_module.field_path(globe_module.find_map('paleoatlas-000')).exists():
                self.skipTest('the 2016 atlas has not been segmented in this checkout')
            response = self.client.get('/globe/fields/paleoatlas-000.png')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response['Content-Type'], 'image/png')

    def test_all_frames_have_calibration_and_local_routes(self):
        with self.settings(SCOTESE_VIEWER_ENABLED=True):
            response = self.client.get('/', {'masks': 'scotese2002'})
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
            frames = self.client.get('/', {'masks': 'scotese2002'}).context['frames']
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

    def test_deep_stops_reach_past_the_oldest_map(self):
        frames = [{'age': age} for age in [650, 100, 0]]
        plan = {'interval_ma': None, 'steps': 2}
        without = globe_module.timeline(frames, plan)
        with_deep = globe_module.timeline(frames, plan, deepest_model=1800)
        self.assertEqual(len(with_deep) - len(without), 46)
        deep = [stop for stop in with_deep if stop[0] < 0]
        self.assertEqual(deep, with_deep[:len(deep)])
        self.assertEqual(deep[0][3], 1800)
        self.assertGreater(deep[-1][3], 650)
        ages = [stop[3] for stop in with_deep]
        self.assertEqual(ages, sorted(ages, reverse=True))
        for stop in deep:
            self.assertEqual(stop[:3], [-1, -1, 0.0])

    def test_no_deep_stops_without_a_model_that_reaches_further(self):
        frames = [{'age': age} for age in [650, 0]]
        plan = {'interval_ma': None, 'steps': 4}
        self.assertEqual(globe_module.timeline(frames, plan, deepest_model=650),
                         globe_module.timeline(frames, plan))
        self.assertEqual(globe_module.timeline(frames, plan, deepest_model=None),
                         globe_module.timeline(frames, plan))
        self.assertEqual(globe_module.deep_stops(650, 660), [])

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
            response = self.client.get('/', {'masks': 'scotese2002'})
            self.assertTrue(response.context['source_maps_public'])
            self.assertTrue(all(frame['url'] for frame in response.context['frames']))

    def test_health_fails_when_the_runtime_bundle_is_missing(self):
        with self.settings(SCOTESE_VIEWER_ENABLED=True, SCOTESE_DERIVED_DIR='/nonexistent',
                           PALEOATLAS_DERIVED_DIR='/nonexistent'):
            response = self.client.get('/healthz')
        self.assertEqual(response.status_code, 503)
        body = response.json()
        self.assertEqual(body['status'], 'unhealthy')
        self.assertEqual(body['fields']['missing'], body['fields']['expected'])
        with self.settings(SCOTESE_VIEWER_ENABLED=False, SCOTESE_DERIVED_DIR='/nonexistent'):
            response = self.client.get('/healthz')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['fields']['required'])

    def test_a_model_without_a_licence_is_locked_rather_than_absent(self):
        restricted = '/plates/torsvikcocks2017/rotations.json'
        with self.settings(SCOTESE_VIEWER_ENABLED=True, ACCESS_KEY=""):
            # With no key configured there is nothing to unlock it with, so it is not
            # offered at all.
            request = RequestFactory().get('/')
            request.session = self.client.session
            offered = {model["id"] for model in globe_module.plate_models(request)}
            self.assertNotIn("torsvikcocks2017", offered)
            self.assertEqual(self.client.get(restricted).status_code, 404)
        with self.settings(SCOTESE_VIEWER_ENABLED=True, ACCESS_KEY="a-key-for-the-test"):
            listed = self.client.get('/').context['plates']
            if not listed:
                self.skipTest("plate models have not been packed in this checkout")
            entry = next(model for model in listed if model["id"] == "torsvikcocks2017")
            self.assertTrue(entry["locked"])
            self.assertFalse(entry["published"])
            response = self.client.get(restricted)
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json()["locked"], True)
            # The site itself is open either way.
            self.assertEqual(self.client.get('/').status_code, 200)
            self.assertEqual(self.client.get('/about/').status_code, 200)
            self.assertEqual(
                self.client.get('/plates/merdith2021/rotations.json').status_code, 200)

            self.client.post('/access/', {"key": "a-key-for-the-test"})
            self.assertEqual(self.client.get(restricted).status_code, 200)
            entry = next(model for model in self.client.get('/').context['plates']
                         if model["id"] == "torsvikcocks2017")
            self.assertFalse(entry["locked"])

    def test_the_gate_answers_json_for_the_viewer(self):
        json_headers = {"HTTP_ACCEPT": "application/json"}
        with self.settings(ACCESS_KEY="a-key-for-the-test"):
            response = self.client.get('/access/', **json_headers)
            self.assertEqual(response.json(), {"granted": False})
            response = self.client.post('/access/', {"key": "wrong"}, **json_headers)
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json(), {"granted": False})
            response = self.client.post('/access/', {"key": "a-key-for-the-test"},
                                        **json_headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"granted": True})

    def test_the_gate_refuses_to_send_a_visitor_off_site(self):
        with self.settings(ACCESS_KEY="a-key-for-the-test"):
            for target in ("https://example.com/", "//example.com/", None):
                response = self.client.post('/access/', {"key": "a-key-for-the-test",
                                                         "next": target or ""})
                self.assertEqual(response["Location"], "/")
                self.client.cookies.clear()

    def test_missing_map_returns_404(self):
        with self.settings(SCOTESE_VIEWER_ENABLED=True):
            with patch('pathlib.Path.open', side_effect=FileNotFoundError):
                with patch('core.globe.catalogue', return_value={'maps': [{'id': 'test', 'image': {'path': 'missing.jpg'}}]}):
                    self.assertEqual(self.client.get('/globe/maps/test.jpg').status_code, 404)
