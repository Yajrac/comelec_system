from unittest.mock import patch
from django.core.cache import cache
from django.http import HttpResponse
from django.test import SimpleTestCase, RequestFactory, override_settings
from core.page_rate_limit import PageRateLimitMiddleware


@override_settings(PAGE_RATE_LIMIT_REQUESTS=3, PAGE_RATE_LIMIT_SECONDS=10, STORAGES={"default": {"BACKEND": "django.core.files.storage.InMemoryStorage"}, "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}})
class PageRateLimitTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.factory = RequestFactory()
        self.middleware = PageRateLimitMiddleware(lambda request: HttpResponse("ok"))

    def tearDown(self):
        cache.clear()

    def test_refresh_burst_returns_friendly_429(self):
        for index in range(3):
            self.assertEqual(self.middleware(self.factory.get("/unknown/" )).status_code, 200)
        response = self.middleware(self.factory.get("/unknown/"))
        self.assertEqual(response.status_code, 429)
        self.assertIn(b"Please slow down", response.content)
        self.assertEqual(response["Retry-After"], "10")
        self.assertEqual(response["Cache-Control"], "no-store")
        cache.clear()
        self.assertEqual(self.middleware(self.factory.get("/unknown/")).status_code, 200)

    def test_device_api_assets_and_login_posts_are_not_counted(self):
        for path in ["/api/find-applicant/", "/comelec/api/signature/waiting/", "/static/test.css", "/media/test.png", "/offline/connection/"]:
            for index in range(5):
                self.assertEqual(self.middleware(self.factory.get(path)).status_code, 200)
        for index in range(5):
            self.assertEqual(self.middleware(self.factory.post("/comelec/admin/")).status_code, 200)

    def test_separate_ips_have_separate_limits(self):
        for index in range(4):
            self.middleware(self.factory.get("/", REMOTE_ADDR="192.0.2.1"))
        self.assertEqual(self.middleware(self.factory.get("/", REMOTE_ADDR="192.0.2.2")).status_code, 200)
