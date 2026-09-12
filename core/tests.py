from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db import OperationalError
from django.test import RequestFactory, TestCase

from config.version import VERSION


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

    def test_missing_map_returns_404(self):
        with self.settings(SCOTESE_VIEWER_ENABLED=True):
            with patch('pathlib.Path.open', side_effect=FileNotFoundError):
                with patch('core.globe.catalogue', return_value={'maps': [{'id': 'test', 'image': {'path': 'missing.jpg'}}]}):
                    self.assertEqual(self.client.get('/globe/maps/test.jpg').status_code, 404)
