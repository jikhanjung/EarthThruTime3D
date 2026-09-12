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
