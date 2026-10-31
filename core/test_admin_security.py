from datetime import timedelta
from io import StringIO
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from core.models import AdminAccountSecurity, AdminLoginThrottle


@override_settings(STORAGES={"default": {"BACKEND": "django.core.files.storage.InMemoryStorage"}, "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}})
class AdminSecurityTests(TestCase):
    def setUp(self):
        self.password = "Desk-Current-8Z!49"
        self.user = get_user_model().objects.create_superuser(username="clientadmin", password=self.password)

    def attempt(self, password):
        return self.client.post(reverse("admin-login"), {"username": "clientadmin", "password": password})

    def test_five_failures_lock_even_correct_password_until_expiry(self):
        for number in range(5):
            response = self.attempt("incorrect")
        self.assertEqual(response.status_code, 429)
        self.assertEqual(self.attempt(self.password).status_code, 429)
        AdminLoginThrottle.objects.update(locked_until=timezone.now() - timedelta(seconds=1))
        response = self.attempt(self.password)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session["_auth_user_id"], str(self.user.pk))

    def test_success_clears_account_failures(self):
        self.attempt("incorrect")
        self.assertEqual(self.attempt(self.password).status_code, 302)
        self.assertEqual(AdminLoginThrottle.objects.count(), 1)

    def test_required_change_cannot_be_bypassed_by_direct_request(self):
        AdminAccountSecurity.objects.create(user=self.user, must_change_password=True)
        self.client.force_login(self.user)
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(response, reverse("admin-change-password"), fetch_redirect_response=False)
        response = self.client.post(reverse("admin-walk-in-form", args=["new"]), {"firstname": "Juan"})
        self.assertEqual(response.url, reverse("admin-change-password"))
        self.assertEqual(self.client.get(reverse("admin-change-password")).status_code, 200)

    def test_password_change_requires_current_password_and_new_password(self):
        AdminAccountSecurity.objects.create(user=self.user, must_change_password=True)
        self.client.force_login(self.user)
        url = reverse("admin-change-password")
        for old, new in [("wrong", "Desk-Replaced-7Y!88"), (self.password, self.password), (self.password, "123")]:
            response = self.client.post(url, {"old_password": old, "new_password1": new, "new_password2": new})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(AdminAccountSecurity.objects.get(user=self.user).must_change_password)
        new = "Desk-Replaced-7Y!88"
        response = self.client.post(url, {"old_password": self.password, "new_password1": new, "new_password2": new})
        self.assertEqual(response.url, reverse("dashboard"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new))
        self.assertFalse(AdminAccountSecurity.objects.get(user=self.user).must_change_password)
        self.assertEqual(self.client.session["_auth_user_id"], str(self.user.pk))

    @patch("core.management.commands.prepare_admin_handover.getpass", side_effect=["Client-Temp-9X!45", "Client-Temp-9X!45"])
    def test_handover_command_creates_flagged_admin_without_changing_existing(self, prompt):
        call_command("prepare_admin_handover", "newclient", stdout=StringIO())
        client = get_user_model().objects.get(username="newclient")
        self.assertTrue(client.is_superuser)
        self.assertTrue(AdminAccountSecurity.objects.get(user=client).must_change_password)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.password))

    def test_ip_limit_covers_different_usernames(self):
        # Start just below the IP threshold without spending time on twenty password hashes.
        from django.utils.crypto import salted_hmac
        key = salted_hmac("admin-ip", "127.0.0.1").hexdigest()
        AdminLoginThrottle.objects.create(key=key, failures=19, window_started=timezone.now())
        self.assertEqual(self.attempt("wrong").status_code, 429)
        response = self.client.post(reverse("admin-login"), {"username": "another", "password": "wrong"})
        self.assertEqual(response.status_code, 429)

    def test_developer_login_uses_same_attempt_limit(self):
        for number in range(5):
            response = self.client.post("/developer/login/", {"username": "clientadmin", "password": "wrong"})
        self.assertEqual(response.status_code, 429)
        self.assertEqual(self.attempt(self.password).status_code, 429)

    def test_live_password_checks_match_server_validators(self):
        self.client.force_login(self.user)
        AdminAccountSecurity.objects.create(user=self.user, must_change_password=True)
        url = reverse("admin-password-requirements")
        response = self.client.post(url, {"password": ""})
        self.assertFalse(any(response.json()["checks"]))
        self.assertFalse(all(self.client.post(url, {"password": "12345678"}).json()["checks"]))
        response = self.client.post(url, {"password": "Desk-Fresh-7V!39"})
        self.assertTrue(all(response.json()["checks"]))
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertNotIn("Desk-Fresh", response.content.decode())
        self.assertContains(self.client.get(reverse("admin-change-password")), "passwordChecklist")

    def test_password_checks_require_admin(self):
        self.assertEqual(self.client.post(reverse("admin-password-requirements"), {"password": "test"}).status_code, 302)
        user = get_user_model().objects.create_user(username="ordinary")
        self.client.force_login(user)
        self.assertEqual(self.client.post(reverse("admin-password-requirements"), {"password": "test"}).status_code, 403)
