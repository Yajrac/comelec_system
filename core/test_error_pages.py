from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(STORAGES={"default": {"BACKEND": "django.core.files.storage.InMemoryStorage"}, "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}})
class ErrorPageTests(TestCase):
    def test_friendly_404_in_debug_and_production(self):
        for debug in [True, False]:
            with override_settings(DEBUG=debug):
                response = self.client.get("/comelec/change-password/hb")
                self.assertEqual(response.status_code, 404)
                self.assertTemplateUsed(response, "errors/404.html")
                self.assertContains(response, "Back to home", status_code=404)
                self.assertNotContains(response, "URL patterns", status_code=404)
                self.assertNotContains(response, "Request Method", status_code=404)

    def test_admin_can_return_to_dashboard(self):
        user = get_user_model().objects.create_superuser(username="errorsadmin", password="test-password")
        self.client.force_login(user)
        response = self.client.get("/missing-page/")
        self.assertContains(response, reverse("dashboard"), status_code=404)

    def test_api_404_stays_json(self):
        with override_settings(DEBUG=True):
            response = self.client.get("/api/no-such-endpoint/")
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response["Content-Type"], "application/json")
            self.assertEqual(response.json()["success"], False)
