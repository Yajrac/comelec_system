import json
from datetime import date
from unittest.mock import patch
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, RequestFactory, override_settings, TestCase
from Applicants.validation import validate_inputs
from api.views import new_registration_api


class InputValidationTests(SimpleTestCase):
    def test_accepts_real_name_characters(self):
        for name in ["Anne-Marie", "O'Connor", "O\u2019Connor", "Dela Cruz", "Ma. Elena", "Pe\u00f1a", "Jose\u0301"]:
            self.assertEqual(validate_inputs({"firstname": name}), {})

    def test_rejects_digits_and_symbol_only_names(self):
        for name in ["Juan123", "Juan?", "123", "@@@", "---", "", "Juan\nCruz", "A" * 256]:
            self.assertIn("firstname", validate_inputs({"firstname": name}))
        self.assertEqual(validate_inputs({"middlename": ""}), {})

    def test_phone_requires_ascii_digits_and_09_prefix(self):
        self.assertEqual(validate_inputs({"phone": "09171234567"}), {})
        for phone in ["0917", "+639171234567", "08171234567", "0917abc4567", "091712345678", "\u0660\u0669" + "1" * 9]:
            self.assertIn("phone", validate_inputs({"phone": phone}))

    def test_email_validation(self):
        self.assertEqual(validate_inputs({"email": "juan@example.com"}), {})
        self.assertEqual(validate_inputs({"email": ""}), {})
        for value in ["bad", "a@", "a b@example.com"]:
            self.assertIn("email", validate_inputs({"email": value}))

    @patch("Applicants.validation.timezone.localdate", return_value=date(2026, 10, 30))
    def test_birthdate_and_age_are_consistent(self, today):
        self.assertEqual(validate_inputs({"birthdate": "2000-11-01", "age": 25}), {})
        self.assertIn("age", validate_inputs({"birthdate": "2000-11-01", "age": 26}))
        for value in ["2026-10-30", "2027-01-01", "2000-02-31", "bad"]:
            self.assertIn("birthdate", validate_inputs({"birthdate": value}))
        for age in [True, 1.5, "-1", "151"]:
            self.assertIn("age", validate_inputs({"age": age}))

    def test_choices_ids_lengths_and_reason(self):
        for data in [{"sex": "other-value"}, {"civil_status": "wrong"}, {"brgy": "1 OR 1=1"}, {"applicant_id": []}, {"reason": ""}, {"birthplace": "x" * 256}]:
            self.assertTrue(validate_inputs(data))

    def test_upload_content_size_and_extension(self):
        good = SimpleUploadedFile("id.pdf", b"%PDF-1.7 content")
        self.assertEqual(validate_inputs({}, {"valid_id_document": good}), {})
        self.assertEqual(good.tell(), 0)
        for name, content in [("id.exe", b"x"), ("id.pdf", b"not pdf"), ("id.png", b"x"), ("id.pdf", b"x" * (5 * 1024 * 1024 + 1))]:
            self.assertIn("valid_id_document", validate_inputs({}, {"valid_id_document": SimpleUploadedFile(name, content)}))

    def test_api_rejects_invalid_fields_before_database_access(self):
        request = RequestFactory().post("/api/new-registration/", data=json.dumps({"firstname": "Juan123", "phone": "123"}), content_type="application/json")
        response = new_registration_api(request)
        self.assertEqual(response.status_code, 400)
        result = json.loads(response.content)
        self.assertIn("firstname", result["errors"])
        self.assertIn("phone", result["errors"])

    def test_api_rejects_non_object_json(self):
        request = RequestFactory().post("/api/new-registration/", data="[]", content_type="application/json")
        self.assertEqual(new_registration_api(request).status_code, 400)


@override_settings(STORAGES={"default": {"BACKEND": "django.core.files.storage.InMemoryStorage"}, "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}})
class UpdateFormPrefillTests(SimpleTestCase):
    def render_form(self, form_data=None):
        from django.template.loader import render_to_string
        from Applicants.models import Applicant, Barangay
        applicant = Applicant(id=1, firstname="Juan", lastname="Cruz", middlename="Reyes",
            birthdate=date(2000, 1, 2), age=26, sex="Male", civil_status="Married",
            pwd_status="HEARING", brgy_id=1)
        return render_to_string("applicant/forms/update_registration.html", {
            "applicant": applicant, "barangays": [Barangay(id=1, name="First"), Barangay(id=2, name="Second")],
            "form_data": form_data or {}, "pwd_choices": Applicant.PWD_CHOICES,
        })

    def test_saved_choices_are_selected(self):
        import re
        html = self.render_form()
        for value in ["MALE", "MARRIED", "HEARING"]:
            self.assertRegex(html, r'<option\s+value="' + value + r'"\s+selected')
        self.assertIn('value="2000-01-02"', html)

    def test_validation_error_retains_changed_date_and_barangay(self):
        html = self.render_form({"birthdate": "2001-03-04", "brgy_id": "2"})
        self.assertIn('value="2001-03-04"', html)
        self.assertRegex(html, r'value="2"\s+selected')

    def test_cleared_optional_name_stays_empty_after_error(self):
        html = self.render_form({"middlename": "", "birthdate": "2000-01-02"})
        self.assertRegex(html, r'id="middlename"[\s\S]*?value=""')


@override_settings(STORAGES={"default": {"BACKEND": "django.core.files.storage.InMemoryStorage"}, "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}})
class UpdateSubmissionTests(TestCase):
    def test_submit_update_creates_request_and_displays_success(self):
        from Applicants.models import Applicant, ApplicantUpdateRequest, Barangay
        from django.urls import reverse
        barangay = Barangay.objects.create(name="Test Barangay")
        applicant = Applicant.objects.create(firstname="Juan", lastname="Cruz", middlename="",
            birthdate=date(2000, 1, 2), age=26, sex="Male", civil_status="Single",
            brgy=barangay, birthplace="Pio Duran", phone="09171234567", email="juan@example.com",
            father="Pedro Cruz", mother="Maria Cruz")
        original = SimpleUploadedFile("original.pdf", b"%PDF-1.7 original document")
        applicant.valid_id_document.save(original.name, original)
        original_name = applicant.valid_id_document.name
        payload = {
            "action": "submit_update", "applicant_id": applicant.pk,
            "firstname": "Juan", "lastname": "Cruz", "middlename": "",
            "birthdate": "2000-01-02", "age": "26", "sex": "MALE", "civil_status": "MARRIED",
            "brgy_id": barangay.pk, "birthplace": "Pio Duran", "municipality": "Pio Duran", "province": "Albay",
            "phone": "09171234567", "email": getattr(self, "submitted_email", "juan@example.com"), "father": "Pedro Cruz", "mother": "Maria Cruz",
            "pwd_status": "HEARING", "citizenship_status": "BY_BIRTH", "reason": "Correct my civil status.",
            "valid_id_document": SimpleUploadedFile("id.pdf", b"%PDF-1.7 sample document"),
        }
        if getattr(self, "reuse_document", False):
            payload.pop("valid_id_document")
        response = self.client.post(getattr(self, "submission_url", reverse("update-registration")), payload)
        self.assertEqual(response.status_code, 302, getattr(response, "context", None))
        application = ApplicantUpdateRequest.objects.get(applicant=applicant)
        if getattr(self, "reuse_document", False):
            self.assertEqual(application.valid_id_document.name, original_name)
        else:
            self.assertNotEqual(application.valid_id_document.name, original_name)
        applicant.refresh_from_db()
        self.assertEqual(applicant.valid_id_document.name, original_name)
        self.assertTrue(applicant.valid_id_document.storage.exists(original_name))
        self.assertEqual(application.email, getattr(self, "submitted_email", "juan@example.com"))
        self.assertEqual(application.civil_status, "Married")
        self.assertEqual(application.pwd_status, "HEARING")
        self.assertEqual(self.client.get(response.url).status_code, 200)
        applicant.refresh_from_db()
        self.assertEqual(applicant.civil_status, "Single")
        for status in ["PENDING", "REVIEW"]:
            application.status = status
            application.save(update_fields=["status"])
            lookup = self.client.post(reverse("update-registration"), {
                "action": "find_applicant", "registration_reference": applicant.registration_reference,
            })
            self.assertContains(lookup, 'id="pendingCorrectionDialog"')
            self.assertNotContains(lookup, 'id="updateRegistrationForm"')
            self.assertEqual(ApplicantUpdateRequest.objects.filter(applicant=applicant).count(), 1)



class OptionalEmailStorageTests(TestCase):
    def test_multiple_applicants_can_skip_email(self):
        from Applicants.models import Applicant
        for name in ["Juan", "Pedro"]:
            Applicant.objects.create(firstname=name, lastname="Cruz", middlename="", email=None,
                age=26, birthdate=date(2000, 1, 2), sex="Male", birthplace="Pio Duran",
                phone="09171234567", father="Jose Cruz", mother="Maria Cruz")
        self.assertEqual(Applicant.objects.filter(email__isnull=True).count(), 2)


@override_settings(STORAGES={"default": {"BACKEND": "django.core.files.storage.InMemoryStorage"}, "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}})
class OptionalRegistrationSubmissionTests(TestCase):
    def test_registration_accepts_blank_middle_name_and_email(self):
        from Applicants.models import Applicant, Barangay
        from django.urls import reverse
        barangay = Barangay.objects.create(name="Test Barangay")
        response = self.client.post(reverse("new-registration"), {
            "firstname": "Juan", "lastname": "Cruz", "middlename": "", "email": "",
            "birthdate": "2000-01-02", "age": "26", "sex": "Male", "civil_status": "Single",
            "brgy": barangay.pk, "brgy_id": barangay.pk, "birthplace": "Pio Duran",
            "municipality": "Pio Duran", "province": "Albay", "phone": "09171234567",
            "father": "Pedro Cruz", "mother": "Maria Cruz", "pwd_status": "NO", "citizenship_status": "BY_BIRTH",
            "valid_id_document": SimpleUploadedFile("id.pdf", b"%PDF-1.7 sample document"),
        })
        self.assertEqual(response.status_code, 302, getattr(response, "context", None))
        applicant = Applicant.objects.get()
        self.assertIsNone(applicant.email)
        self.assertEqual(applicant.middlename, "")


class UpdateExistingDocumentTests(UpdateSubmissionTests):
    reuse_document = True


class UpdateBlankEmailTests(UpdateSubmissionTests):
    submitted_email = ""

    def test_missing_email_prefills_as_empty(self):
        from django.template.loader import render_to_string
        from Applicants.models import Applicant
        applicant = Applicant(firstname="Juan", lastname="Cruz", email=None,
            birthdate=date(2000, 1, 2), age=26)
        html = render_to_string("applicant/forms/update_registration.html", {
            "applicant": applicant, "form_data": {}, "barangays": [],
        })
        self.assertRegex(html, r'id="email"[\s\S]*?value=""')
        email_input = html.split('id="email"', 1)[1].split('>', 1)[0]
        self.assertNotIn('required', email_input)
        self.assertNotIn('None', email_input)
