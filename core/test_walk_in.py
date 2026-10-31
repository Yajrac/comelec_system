from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(STORAGES={"default": {"BACKEND": "django.core.files.storage.InMemoryStorage"}, "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}})
class WalkInTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(username="walkinadmin", password="test-password")

    def test_anonymous_and_non_admin_cannot_access(self):
        url = reverse("admin-walk-in-form", args=["new"])
        self.assertEqual(self.client.get(url).status_code, 302)
        user = get_user_model().objects.create_user(username="ordinary", password="test-password")
        self.client.force_login(user)
        response = self.client.get(url)
        self.assertNotEqual(response.status_code, 200)

    def test_admin_sees_service_cards_and_admin_forms(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("admin-walk-in"))
        self.assertContains(response, "APPLICATION FOR NEW REGISTRATION")
        for service in ["new", "update", "transfer", "reactivation", "reinstatement"]:
            response = self.client.get(reverse("admin-walk-in-form", args=[service]))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'id="adminDesktopSidebar"')
            self.assertContains(response, reverse("admin-walk-in"))

    def test_invalid_submission_stays_in_admin_layout(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("admin-walk-in-form", args=["new"]), {"firstname": "Invalid123"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="adminDesktopSidebar"')

    def test_invalid_service_is_not_found(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("admin-walk-in-form", args=["unknown"])).status_code, 404)

    def test_directory_search_by_name_and_reference_and_start_service(self):
        from datetime import date
        from Applicants.models import Applicant, ApplicantUpdateRequest
        applicant = Applicant.objects.create(lastname="Cruz", firstname="Juan", middlename="",
            birthdate=date(2000, 1, 2), age=26, sex="Male", birthplace="Pio Duran",
            phone="09171234567", email="walkin@example.com", father="Pedro", mother="Maria")
        self.client.force_login(self.admin)
        for search in ["Juan Cruz", applicant.registration_reference]:
            response = self.client.get(reverse("admin-walk-in"), {"search": search})
            self.assertContains(response, applicant.registration_reference)
            self.assertEqual(response.context["records"].paginator.count, 1)
        response = self.client.get(reverse("admin-walk-in"), {"search": "not-found"})
        self.assertContains(response, "No applicant records found")
        response = self.client.post(reverse("admin-walk-in-form", args=["update"]), {
            "action": "find_applicant", "registration_reference": applicant.registration_reference,
        })
        self.assertContains(response, 'value="Juan"')
        self.assertContains(response, 'id="submitUpdateButton"')
        self.assertFalse(ApplicantUpdateRequest.objects.exists())


from Applicants.test_validation import UpdateSubmissionTests as _UpdateSubmissionTests


class WalkInSubmissionTests(_UpdateSubmissionTests):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(username="walkinsubmit", password="test-password")
        self.client.force_login(self.admin)
        self.submission_url = reverse("admin-walk-in-form", args=["update"])

    def test_submit_update_creates_request_and_displays_success(self):
        super().test_submit_update_creates_request_and_displays_success()
        from Applicants.models import ApplicantUpdateRequest
        application = ApplicantUpdateRequest.objects.get()
        response = self.client.get(reverse("admin-walk-in-success", args=["update", application.pk]))
        self.assertContains(response, 'id="adminDesktopSidebar"')
