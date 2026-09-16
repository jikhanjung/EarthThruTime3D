import json
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
                # The version sits beside the name in the header, not in the footer.
                self.assertContains(response, f'Earth Thru Time <span class="brand-version">v{VERSION}</span>')
                self.assertContains(response, "PaleoBytes")
                self.assertNotContains(response, f"PaleoBytes · v{VERSION}")

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
        self.assertNotContains(response, 'id="relief3d"', msg_prefix='no 3D terrain without heights')
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

    def test_the_elevation_series_carries_names_and_rotation_motions_where_computed(self):
        with self.settings(SCOTESE_VIEWER_ENABLED=True):
            response = self.client.get('/', {'masks': 'paleodem2018'})
        if response.context['mask']['id'] != 'paleodem2018':
            self.skipTest('the elevation series has not been built in this checkout')
        frames = response.context['frames']
        motions = response.context['motions']
        if not motions:
            self.skipTest('elevation motions have not been computed in this checkout')
        self.assertEqual(len(motions), len(frames) - 1)
        self.assertTrue(all(frame['names'] for frame in frames), 'every grid borrows its names')
        named = {frame['id']: {name['name'] for name in frame['names']} for frame in frames}
        self.assertIn('아프리카', named['paleodem-0000'])
        self.assertIn('로렌시아', named['paleodem-4200'])
        self.assertTrue(all(gap for gap in motions), 'every gap carries at least one landmass')
        for gap in motions:
            self.assertLessEqual(len(gap), globe_module.MAX_MOTIONS)

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

    def test_fossil_coastlines_are_offered_over_the_atlas_but_not_the_2002_maps(self):
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
        self.assertNotContains(response, '시간을 돌려, 지구를 보다')
        self.assertContains(response, 'class="brand-version"')
        # The map page: the inspector folds away and one panel holds every control.
        self.assertContains(response, 'id="info-toggle"')
        self.assertContains(response, '<section class="controls"')
        # The toolbar keeps the essentials; the rest of the view settings sit behind the menu.
        self.assertContains(response, 'id="settings-toggle"')
        self.assertContains(response, 'id="settings-menu" role="group"')
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


class PaleodemTests(TestCase):
    """The elevation series: PaleoDEM grids as a third mask source, fronted by the atlas."""

    def setUp(self):
        self.dem = TemporaryDirectory()
        self.atlas = TemporaryDirectory()
        self.addCleanup(self.dem.cleanup)
        self.addCleanup(self.atlas.cleanup)
        override = self.settings(SCOTESE_VIEWER_ENABLED=True, PALEODEM_DERIVED_DIR=self.dem.name,
                                 PALEOATLAS_DERIVED_DIR=self.atlas.name)
        override.enable()
        self.addCleanup(override.disable)

    def build(self, item):
        globe_module.field_path(item).write_bytes(b'png')

    def test_series_is_the_grids_fronted_by_the_atlas_beyond_540_ma(self):
        items = globe_module.series_items('paleodem2018')
        self.assertEqual(len(items), 112)
        self.assertEqual([item['age_ma'] for item in items[:3]], [750.0, 690.0, 600.0])
        self.assertEqual(items[3]['id'], 'paleodem-5400')
        self.assertEqual(items[-1]['id'], 'paleodem-0000')
        self.assertEqual([globe_module.source_of(items[0]), globe_module.source_of(items[3])],
                         ['paleoatlas2016', 'paleodem2018'])
        self.assertEqual(len({item['id'] for item in items}), 112)

    def test_a_visitor_gets_the_series_only_once_it_is_whole(self):
        request = RequestFactory().get('/', {'masks': 'paleodem2018'})
        self.assertEqual(globe_module.mask_source(request), 'paleoatlas2016')
        self.assertNotContains(self.client.get('/'), '?masks=paleodem2018',
                               msg_prefix='no comparison link to a series that cannot be shown')
        self.assertNotContains(self.client.get('/'), 'value="paleodem2018"',
                               msg_prefix='nor a dataset choice')
        items = globe_module.series_items('paleodem2018')
        for item in items[1:]:
            self.build(item)
        self.assertEqual(globe_module.mask_source(request), 'paleoatlas2016',
                         'the atlas prelude counts: a partial build has frames that cannot render')
        self.build(items[0])
        self.assertEqual(globe_module.mask_source(request), 'paleodem2018')
        self.assertContains(self.client.get('/'), '?masks=paleodem2018')

    def test_the_setting_is_trusted_and_health_reports_what_is_missing(self):
        # Like the other sources: a configured series is served as it is, and a partial
        # build fails the health check instead of quietly showing something else.
        items = globe_module.series_items('paleodem2018')
        self.build(items[-1])
        with self.settings(MASK_SOURCE='paleodem2018'):
            self.assertEqual(globe_module.mask_source(), 'paleodem2018')
            self.assertEqual(self.client.get('/').context['mask']['id'], 'paleodem2018')
            response = self.client.get('/healthz')
        self.assertEqual(response.status_code, 503)
        report = response.json()['fields']
        self.assertEqual((report['source'], report['expected'], report['missing']), ('paleodem2018', 112, 111))

    def test_fossil_coastlines_are_offered_over_the_series(self):
        for item in globe_module.series_items('paleodem2018'):
            self.build(item)
        response = self.client.get('/', {'masks': 'paleodem2018'})
        if response.context['coastlines'] is None:
            self.skipTest('PaleoCoastlines have not been packed in this checkout')
        self.assertContains(response, 'id="coastline"')

    def test_the_english_page_has_no_korean_left(self):
        for item in globe_module.series_items('paleodem2018'):
            self.build(item)
        response = self.client.get('/', {'masks': 'paleodem2018'}, HTTP_ACCEPT_LANGUAGE='en')
        self.assertEqual(response['Content-Language'], 'en')
        self.assertNotRegex(response.content.decode(), '[가-힣]')

    def test_frames_carry_relief_and_period_labels(self):
        for item in globe_module.series_items('paleodem2018'):
            self.build(item)
        response = self.client.get('/', {'masks': 'paleodem2018'})
        frames = response.context['frames']
        self.assertEqual(response.context['mask']['id'], 'paleodem2018')
        self.assertTrue(response.context['mask']['relief'])
        self.assertEqual(len(frames), 112)
        self.assertEqual([frame['relief'] for frame in frames[:4]], [False, False, False, True])
        self.assertTrue(all(frame['relief'] for frame in frames[3:]))
        self.assertTrue(all(frame['url'] is None and frame['bounds'] is None for frame in frames))
        self.assertEqual(frames[-1]['label'], '현재')
        self.assertEqual(frames[3]['title'], 'Cambrian Precambrian boundary')
        self.assertTrue(all(frame['field'] == f"/globe/fields/{frame['id']}.png" for frame in frames))
        self.assertEqual(frames[-1]['source'], 'https://zenodo.org/records/5460860')
        self.assertContains(response, 'id="surface"')
        self.assertContains(response, 'id="shading"')
        # 3D terrain belongs to the series with heights, and says it is exaggerated.
        self.assertContains(response, 'id="relief3d"')
        self.assertContains(response, 'id="relief-note"')
        self.assertContains(response, 'zenodo.org/records/5460860')
        self.assertContains(response, '?masks=paleoatlas2016')
        self.assertContains(response, '?masks=scotese2002')
        self.assertEqual(sorted(dict(response.context['mask']['others'])), ['paleoatlas2016', 'scotese2002'])
        # The panel's dataset picker offers all three, the shown one selected.
        self.assertEqual([choice[0] for choice in response.context['mask']['choices']],
                         ['paleoatlas2016', 'paleodem2018', 'scotese2002'])
        self.assertContains(response, 'title="PALEOMAP PaleoDEM 고도 격자 (2018)" selected>고도 격자</option>')
        self.assertContains(self.client.get('/'), 'title="PALEOMAP PaleoDEM 고도 격자 (2018)">고도 격자</option>')

    def test_health_counts_the_series_when_it_is_the_default(self):
        for item in globe_module.series_items('paleodem2018'):
            self.build(item)
        with self.settings(MASK_SOURCE='paleodem2018'):
            report = self.client.get('/healthz').json()['fields']
        self.assertEqual((report['source'], report['expected'], report['missing']), ('paleodem2018', 112, 0))

    def test_temperature_is_optional_and_follows_the_curve_file(self):
        for item in globe_module.series_items('paleodem2018'):
            self.build(item)
        response = self.client.get('/', {'masks': 'paleodem2018'})
        self.assertFalse(response.context['temperature_available'])
        self.assertEqual(response.context['temperature_curve'], [])
        self.assertNotContains(response, 'id="temperature"')
        self.assertNotContains(response, 'id="temp-strip"')
        self.assertNotContains(response, 'id="temp-legend"')
        item = globe_module.catalogue('paleodem2018')['maps'][-1]
        Path(self.dem.name, 'paleotemp-curve.json').write_text(json.dumps(
            {"curve": [[540, 27.5], [0, 14.3]], "stops": {item['id']: {"map_ma": 0, "mean_c": 14.31}}}))
        globe_module.temperature_path(item).write_bytes(b'png')
        response = self.client.get('/', {'masks': 'paleodem2018'})
        self.assertTrue(response.context['temperature_available'])
        self.assertEqual(response.context['temperature_curve'], [[540, 27.5], [0, 14.3]])
        frames = {frame['id']: frame for frame in response.context['frames']}
        self.assertEqual(frames[item['id']]['temp'], f"/globe/temps/{item['id']}.png")
        self.assertEqual(frames[item['id']]['mean_c'], 14.31)
        self.assertIsNone(frames['paleoatlas-600']['temp'])
        self.assertIsNone(frames['paleoatlas-600']['mean_c'])
        for needle in ('id="temperature"', 'id="temp-strip"', 'id="mean-temp"', 'id="temp-legend"',
                       'id="temp-today"', 'zenodo.org/records/8238875'):
            self.assertContains(response, needle)
        self.assertEqual(self.client.get(f"/globe/temps/{item['id']}.png").status_code, 200)
        self.assertEqual(self.client.get('/globe/temps/paleoatlas-600.png').status_code, 404)
        self.assertEqual(self.client.get('/globe/temps/nope.png').status_code, 404)
        # The other sources never carry temperature.
        response = self.client.get('/')
        self.assertFalse(response.context['temperature_available'])

    def test_sea_level_is_optional_and_gives_each_grid_a_datum(self):
        for item in globe_module.series_items('paleodem2018'):
            self.build(item)
        response = self.client.get('/', {'masks': 'paleodem2018'})
        self.assertFalse(response.context['sealevel_available'])
        self.assertNotContains(response, 'id="sealevel"')
        self.assertNotContains(response, 'id="sea-strip"')
        last = globe_module.catalogue('paleodem2018')['maps'][-1]['id']
        Path(self.dem.name, 'sealevel-curve.json').write_text(json.dumps(
            {"long": [[540, 48.1, 26.7, 63.9, 0.0], [0, 0, 0, 0, 23.5]], "pleistocene": [[0, 8.5], [798, -92.4]],
             "stops": {last: 0.0}}))
        response = self.client.get('/', {'masks': 'paleodem2018'})
        self.assertTrue(response.context['sealevel_available'])
        self.assertEqual(response.context['sealevel']['long'][0], [540, 48.1, 26.7, 63.9, 0.0])
        self.assertEqual(len(response.context['sealevel']['pleistocene']), 2)
        frames = {frame['id']: frame for frame in response.context['frames']}
        self.assertEqual(frames[last]['sea_m'], 0.0)
        self.assertIsNone(frames['paleoatlas-600']['sea_m'])
        for needle in ('id="sealevel"', 'id="sea-strip"', 'id="pleistocene"', 'id="sea-level"', 'doi.org/10.25921/RD66-5820'):
            self.assertContains(response, needle)
        self.assertFalse(self.client.get('/').context['sealevel_available'])

    def test_river_fields_are_offered_only_where_built(self):
        for item in globe_module.series_items('paleodem2018'):
            self.build(item)
        response = self.client.get('/', {'masks': 'paleodem2018'})
        self.assertTrue(all(frame['rivers'] is None for frame in response.context['frames']))
        self.assertFalse(response.context['rivers_available'])
        self.assertNotContains(response, 'id="rivers"')
        present = globe_module.catalogue('paleodem2018')['maps'][-1]
        self.assertEqual(self.client.get(f"/globe/rivers/{present['id']}.png").status_code, 404)
        globe_module.rivers_path(present).write_bytes(b'png')
        response = self.client.get('/', {'masks': 'paleodem2018'})
        frames = {frame['id']: frame for frame in response.context['frames']}
        self.assertEqual(frames[present['id']]['rivers'], f"/globe/rivers/{present['id']}.png")
        self.assertIsNone(frames['paleodem-0050']['rivers'])
        self.assertTrue(response.context['rivers_available'])
        self.assertContains(response, 'id="rivers"')
        self.assertContains(response, 'id="river-note"')
        self.assertEqual(self.client.get(f"/globe/rivers/{present['id']}.png").status_code, 200)
        self.assertEqual(self.client.get('/globe/rivers/nope.png').status_code, 404)
        # The lowstand field rides along only where it exists and the slider goes below the
        # datum; its level is the bottom of the ice sidecar's range.
        self.assertIsNone(frames[present['id']]['rivers_low'])
        self.assertEqual(self.client.get(f"/globe/rivers-low/{present['id']}.png").status_code, 404)
        globe_module.rivers_low_path(present).write_bytes(b'png')
        frames = {frame['id']: frame for frame in self.client.get('/', {'masks': 'paleodem2018'}).context['frames']}
        self.assertIsNone(frames[present['id']]['rivers_low'], 'no range known, so no level to mix toward')
        Path(self.dem.name, 'ice-sources.json').write_text(json.dumps(
            {'grids': {present['id']: 'natural-earth'},
             'sheets': {present['id']: {'volume': 26.0, 'areas': [0.3, 0.0], 'range_m': [-130, 60]}}}))
        globe_module.ice_path(present).write_bytes(b'png')
        frames = {frame['id']: frame for frame in self.client.get('/', {'masks': 'paleodem2018'}).context['frames']}
        self.assertEqual(frames[present['id']]['rivers_low'],
                         {'url': f"/globe/rivers-low/{present['id']}.png", 'level_m': -130})
        self.assertEqual(self.client.get(f"/globe/rivers-low/{present['id']}.png").status_code, 200)
        # The fields routed over the ice ride along from their sidecar: only the steps that
        # lower the sea below every younger step's, and only where the file exists.
        self.assertIsNone(frames[present['id']]['rivers_ice'])
        self.assertEqual(self.client.get(f"/globe/rivers-ice/{present['id']}/12500.png").status_code, 404)
        Path(self.dem.name, f"{present['id']}-rivers-ice.json").write_text(json.dumps(
            {'slices': [{'age_ka': 2.5, 'level_m': 0.0, 'lowers': False}, {'age_ka': 12.5, 'level_m': -57.1, 'lowers': True},
                        {'age_ka': 15, 'level_m': -86.1, 'lowers': True}, {'age_ka': 20, 'level_m': -117.0, 'lowers': True}]}))
        for years in (2500, 12500, 20000):
            globe_module.rivers_ice_path(present, years).write_bytes(b'png')
        frames = {frame['id']: frame for frame in self.client.get('/', {'masks': 'paleodem2018'}).context['frames']}
        self.assertEqual(frames[present['id']]['rivers_ice'],
                         [{'age_ka': 12.5, 'level_m': -57.1, 'url': f"/globe/rivers-ice/{present['id']}/12500.png"},
                          {'age_ka': 20, 'level_m': -117.0, 'url': f"/globe/rivers-ice/{present['id']}/20000.png"}])
        self.assertIsNone(frames['paleodem-0050']['rivers_ice'])
        self.assertEqual(self.client.get(f"/globe/rivers-ice/{present['id']}/12500.png").status_code, 200)
        self.assertEqual(self.client.get(f"/globe/rivers-ice/{present['id']}/15000.png").status_code, 404)
        self.assertEqual(self.client.get('/globe/rivers-ice/paleodem-0050/12500.png').status_code, 404)

    def test_ice_mask_is_offered_only_where_built(self):
        for item in globe_module.series_items('paleodem2018'):
            self.build(item)
        response = self.client.get('/', {'masks': 'paleodem2018'})
        self.assertTrue(all(frame['ice'] is None for frame in response.context['frames']))
        self.assertFalse(response.context['ice_available'])
        self.assertNotContains(response, 'id="ice"')
        present = globe_module.catalogue('paleodem2018')['maps'][-1]
        self.assertEqual(self.client.get(f"/globe/ice/{present['id']}.png").status_code, 404)
        globe_module.ice_path(present).write_bytes(b'png')
        response = self.client.get('/', {'masks': 'paleodem2018'})
        frames = {frame['id']: frame for frame in response.context['frames']}
        self.assertEqual(frames[present['id']]['ice'], f"/globe/ice/{present['id']}.png")
        self.assertIsNone(frames['paleodem-0050']['ice'])
        self.assertTrue(response.context['ice_available'])
        self.assertContains(response, 'id="ice"')
        self.assertEqual(self.client.get(f"/globe/ice/{present['id']}.png").status_code, 200)
        self.assertEqual(self.client.get('/globe/ice/nope.png').status_code, 404)
        past = next(item for item in globe_module.catalogue('paleodem2018')['maps'] if item['id'] == 'paleodem-3000')
        globe_module.ice_path(past).write_bytes(b'png')
        frames = {frame['id']: frame for frame in self.client.get('/', {'masks': 'paleodem2018'}).context['frames']}
        self.assertEqual(frames['paleodem-3000']['ice'], '/globe/ice/paleodem-3000.png')
        self.assertIsNone(frames['paleodem-2000']['ice'])
        # The kind of each mask rides along from the builder's sidecar: a cap at a modelled
        # limit is flagged so the page can say it is not an outline.
        self.assertIsNone(frames['paleodem-3000']['ice_kind'])
        Path(self.dem.name, 'ice-sources.json').write_text(json.dumps(
            {'grids': {'paleodem-3000': 'atlas', 'paleodem-1400': 'limit'},
             'sheets': {'paleodem-3000': {'volume': 29.4, 'areas': [0.2, 0.1, 0.0], 'range_m': [-50, 80]}},
             'lows': {present['id']: [{'age_ka': 9, 'level_m': -11.6, 'volume': 28.1, 'areas': [0.3, 0.1, 0.0]},
                                      {'age_ka': 24, 'level_m': -130, 'volume': 75.5, 'areas': [0.4, 0.2, 0.0]},
                                      {'age_ka': 25, 'level_m': -131, 'volume': 76.0, 'areas': [0.4, 0.2, 0.0]}]}}))
        globe_module.ice_low_path(present, 9).write_bytes(b'png')
        globe_module.ice_low_path(present, 24).write_bytes(b'png')
        capped = next(item for item in globe_module.catalogue('paleodem2018')['maps'] if item['id'] == 'paleodem-1400')
        globe_module.ice_path(capped).write_bytes(b'png')
        response = self.client.get('/', {'masks': 'paleodem2018'})
        frames = {frame['id']: frame for frame in response.context['frames']}
        self.assertEqual(frames['paleodem-3000']['ice_kind'], 'atlas')
        self.assertEqual(frames['paleodem-1400']['ice_kind'], 'limit')
        self.assertIsNone(frames[present['id']]['ice_kind'])
        self.assertContains(response, 'id="ice-limit-note"')
        # The volume and area table ride along, and the drawn lowstand where one exists.
        self.assertEqual(frames['paleodem-3000']['ice_sheet']['volume'], 29.4)
        self.assertEqual(frames['paleodem-3000']['ice_sheet']['range_m'], [-50, 80])
        self.assertIsNone(frames['paleodem-1400']['ice_sheet'])
        # The dated lowstand slices ride along where their files exist, youngest first.
        self.assertEqual(frames['paleodem-3000']['ice_lows'], [])
        self.assertIsNone(frames['paleodem-2000']['ice_lows'])
        lows = frames[present['id']]['ice_lows']
        self.assertEqual([(low['age_ka'], low['level_m'], low['url']) for low in lows],
                         [(9, -11.6, f"/globe/ice-low/{present['id']}/9.png"),
                          (24, -130, f"/globe/ice-low/{present['id']}/24.png")])
        self.assertEqual(self.client.get(f"/globe/ice-low/{present['id']}/24.png").status_code, 200)
        self.assertEqual(self.client.get(f"/globe/ice-low/{present['id']}/25.png").status_code, 404)
        self.assertEqual(self.client.get('/globe/ice-low/paleodem-3000/24.png').status_code, 404)
        self.assertFalse(self.client.get('/').context['ice_available'])

    def test_the_time_window_steps_through_the_deglacial_slices(self):
        for item in globe_module.series_items('paleodem2018'):
            self.build(item)
        present = globe_module.catalogue('paleodem2018')['maps'][-1]
        # Without slices there is no window to offer, and asking for one gives the series.
        response = self.client.get('/', {'masks': 'paleodem2018', 'window': 'deglacial'})
        self.assertIsNone(response.context['window'])
        self.assertEqual(len(response.context['frames']), 112)
        self.assertNotContains(response, 'id="window"')
        globe_module.ice_path(present).write_bytes(b'png')
        lows = [{'age_ka': ka, 'level_m': level, 'lowers': lowers, 'volume': 30.0, 'areas': [0.3, 0.0]}
                for ka, level, lowers in [(1, 0.0, False), (2, -5.0, True), (3, -5.0, False)]]
        Path(self.dem.name, 'ice-sources.json').write_text(json.dumps(
            {'grids': {present['id']: 'natural-earth'},
             'sheets': {present['id']: {'volume': 26.0, 'areas': [0.3, 0.0], 'range_m': [-130, 60]}},
             'lows': {present['id']: lows}}))
        for low in lows:
            globe_module.ice_low_path(present, low['age_ka']).write_bytes(b'png')
        response = self.client.get('/', {'masks': 'paleodem2018'})
        self.assertIsNone(response.context['window'])
        self.assertIsNone(response.context['sampling']['window'])
        self.assertContains(response, 'id="window"')
        self.assertContains(response, 'id="sampling"')
        # The what-if keeps only the slices that lower the sea.
        self.assertEqual([low['age_ka'] for low in response.context['frames'][-1]['ice_lows']], [2])
        response = self.client.get('/', {'masks': 'paleodem2018', 'window': 'deglacial'})
        self.assertEqual(response.context['window'], 'deglacial')
        self.assertEqual(response.context['sampling']['window'], 'deglacial')
        self.assertNotContains(response, 'id="sampling"')
        self.assertContains(response, '<option value="deglacial" selected>')
        frames = response.context['frames']
        self.assertEqual([frame['deglacial']['age_ka'] for frame in frames], [3, 2, 1, 0])
        self.assertEqual([frame['age'] for frame in frames], [0.003, 0.002, 0.001, 0])
        self.assertEqual(frames[0]['deglacial'],
                         {'age_ka': 3, 'level_m': -5.0, 'url': f"/globe/ice-low/{present['id']}/3.png"})
        self.assertEqual(frames[-1]['deglacial'], {'age_ka': 0, 'level_m': 0.0, 'url': None})
        self.assertEqual([frame['label'] for frame in frames], ['홀로세', '홀로세', '홀로세', '현재'])
        # The age sets the sea level, so no frame carries a sheet for the slider to range over.
        self.assertTrue(all(frame['ice_sheet'] is None and frame['ice_lows'] is None for frame in frames))
        # Nor a temperature: the present's 5 Myr map says nothing about a glacial maximum.
        self.assertTrue(all(frame['temp'] is None and frame['mean_c'] is None for frame in frames))
        self.assertTrue(all(frame['field'] == f"/globe/fields/{present['id']}.png" for frame in frames))
        # One stop per frame and nothing older: the plate models' deep stops belong to the series.
        self.assertEqual(response.context['stops'],
                         [[0, 1, 0.0, 0.003], [1, 2, 0.0, 0.002], [2, 3, 0.0, 0.001], [3, 3, 0.0, 0]])
        english = self.client.get('/', {'masks': 'paleodem2018', 'window': 'deglacial'}, HTTP_ACCEPT_LANGUAGE='en')
        self.assertNotRegex(english.content.decode(), '[가-힣]')
        # Only the elevation series has a window, and only the listed one.
        self.assertIsNone(self.client.get('/', {'window': 'deglacial'}).context['window'])
        self.assertIsNone(self.client.get('/', {'masks': 'paleodem2018', 'window': 'nope'}).context['window'])

    def test_the_last_glacial_cycle_borrows_the_retreat_where_no_slice_exists(self):
        for item in globe_module.series_items('paleodem2018'):
            self.build(item)
        present = globe_module.catalogue('paleodem2018')['maps'][-1]
        globe_module.ice_path(present).write_bytes(b'png')
        lows = [{'age_ka': 1, 'level_m': 0.0, 'lowers': False, 'volume': 26.0, 'areas': [0.3, 0.0]},
                {'age_ka': 2, 'level_m': -5.0, 'lowers': True, 'volume': 28.0, 'areas': [0.3, 0.0]}]
        Path(self.dem.name, 'ice-sources.json').write_text(json.dumps(
            {'grids': {present['id']: 'natural-earth'},
             'sheets': {present['id']: {'volume': 26.0, 'areas': [0.3, 0.0], 'range_m': [-130, 60]}},
             'lows': {present['id']: lows}}))
        for low in lows:
            globe_module.ice_low_path(present, low['age_ka']).write_bytes(b'png')
        # The stack starts high and swings: past the slices its own level is used, not held.
        Path(self.dem.name, 'sealevel-curve.json').write_text(json.dumps(
            {'long': [[540, 48.1, 26.7, 63.9, 0.0], [0, 0, 0, 0, 23.5]],
             'pleistocene': [[0, 9.0], [1, 7.7], [2, -3.0], [3, -60.0], [4, 0.4]], 'stops': {}}))
        response = self.client.get('/', {'masks': 'paleodem2018', 'window': 'lastcycle'})
        self.assertEqual(response.context['window'], 'lastcycle')
        self.assertContains(response, '<option value="lastcycle" selected>')
        frames = response.context['frames']
        self.assertEqual([(frame['deglacial']['age_ka'], frame['deglacial']['level_m'], frame['ice_kind'])
                          for frame in frames],
                         [(4, 0.4, 'analogue'), (3, -60.0, 'analogue'), (2, -5.0, 'dated'), (1, 0.0, 'dated'),
                          (0, 0.0, 'natural-earth')])
        # An analogue frame keeps the what-if slices and the sheet, which the page mixes at the
        # stack's level; a dated frame has its slice and nothing to mix.
        self.assertIsNone(frames[1]['deglacial']['url'])
        self.assertEqual([low['age_ka'] for low in frames[1]['ice_lows']], [2])
        self.assertEqual(frames[1]['ice_sheet']['volume'], 26.0)
        self.assertEqual(frames[2]['deglacial']['url'], f"/globe/ice-low/{present['id']}/2.png")
        self.assertIsNone(frames[2]['ice_lows'])
        self.assertTrue(all(frame['temp'] is None for frame in frames))
        self.assertEqual(len(response.context['stops']), 5)
        english = self.client.get('/', {'masks': 'paleodem2018', 'window': 'lastcycle'}, HTTP_ACCEPT_LANGUAGE='en')
        self.assertNotRegex(english.content.decode(), '[가-힣]')

    def test_grids_borrow_the_pieces_of_the_nearest_atlas_map(self):
        def report(name):
            return json.dumps({'pieces': [{'names': [{'name': name, 'lon': 1.0, 'lat': 2.0}]}]})
        (Path(self.atlas.name) / 'paleoatlas-255-pieces.json').write_text(report('아프리카'))
        (Path(self.atlas.name) / 'paleoatlas-200-pieces.json').write_text(report('로렌시아'))
        grid = lambda age: {'id': f'paleodem-{int(age * 10):04d}', 'age_ma': age, 'file': 'x.nc'}
        names = lambda item: [name['name'] for name in globe_module.landmass_names(globe_module.piece_report(item))]
        self.assertEqual(globe_module.nearest_atlas_map(255)['id'], 'paleoatlas-255')
        self.assertEqual(names(grid(255)), ['아프리카'], 'the same age: the map itself')
        self.assertEqual(names(grid(205)), ['로렌시아'], 'no map at 205 Ma: the nearest within 5 Myr')
        self.assertIsNone(globe_module.nearest_atlas_map(650), 'nothing within 5 Myr')
        self.assertEqual(names(grid(650)), [])

    def test_series_motions_come_from_their_own_packed_file(self):
        frames = [{'id': item['id']} for item in globe_module.series_items('paleodem2018')]
        self.assertEqual(globe_module.atlas_motions(frames, 'paleodem2018'), [])
        gaps = [{'from': a['id'], 'to': b['id'], 'pairs': [{'lon': 1}]} for a, b in zip(frames, frames[1:])]
        (Path(self.dem.name) / 'motions.json').write_text(json.dumps({'gaps': gaps}))
        self.assertEqual(len(globe_module.atlas_motions(frames, 'paleodem2018')), 111)
        self.assertEqual(globe_module.atlas_motions(frames), [], 'the atlas keeps its own file')
        for item in globe_module.series_items('paleodem2018'):
            self.build(item)
        response = self.client.get('/', {'masks': 'paleodem2018'})
        self.assertEqual(len(response.context['motions']), 111)
        self.assertEqual(response.context['motions'][0], [{'lon': 1}])

    def test_field_route_serves_a_paleodem_slice(self):
        item = globe_module.catalogue('paleodem2018')['maps'][-1]
        self.assertEqual(self.client.get(f"/globe/fields/{item['id']}.png").status_code, 404)
        self.build(item)
        response = self.client.get(f"/globe/fields/{item['id']}.png")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/png')
        self.assertEqual(self.client.get(f"/globe/maps/{item['id']}.jpg").status_code, 404)
