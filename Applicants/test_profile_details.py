from datetime import date
import json
from io import BytesIO
from unittest.mock import patch

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template.loader import render_to_string
from django.test import SimpleTestCase, TestCase, RequestFactory, override_settings
from django.urls import reverse

from Applicants.models import (Applicant, ApplicantUpdateRequest, ApplicantTransferRequest,
                               ApplicantReactivationRequest, ApplicantReinstatementRequest, Barangay)
from Applicants.validation import validate_inputs


def photo(name="selfie.png", image_format="PNG"):
    buffer = BytesIO()
    Image.new("RGB", (12, 12), "blue").save(buffer, format=image_format)
    return SimpleUploadedFile(name, buffer.getvalue())


class ProfileValidationTests(SimpleTestCase):
    def test_photo_must_be_a_real_supported_image(self):
        for name, fmt in [("selfie.png", "PNG"), ("selfie.jpg", "JPEG"), ("selfie.jpeg", "JPEG")]:
            upload = photo(name, fmt)
            self.assertEqual(validate_inputs({}, {"photo": upload}), {})
            self.assertEqual(upload.tell(), 0)
        for upload in [SimpleUploadedFile("selfie.png", b"\x89PNG\r\n\x1a\ninvalid"),
                       SimpleUploadedFile("selfie.pdf", b"%PDF-1.7"),
                       SimpleUploadedFile("selfie.png", b"x" * (5 * 1024 * 1024 + 1)),
                       photo("selfie.jpg", "PNG")]:
            with self.subTest(name=upload.name, size=upload.size):
                self.assertIn("photo", validate_inputs({}, {"photo": upload}))
                self.assertEqual(upload.tell(), 0)

    def test_suffix_and_checkboxes(self):
        for suffix in ("", "Jr.", "Sr.", "II", "III", "IV", "V"):
            self.assertEqual(validate_inputs({"suffix": suffix}), {})
        self.assertIn("suffix", validate_inputs({"suffix": "VI"}))
        self.assertEqual(validate_inputs({"is_indigenous": "on", "is_illiterate": "on"}), {})
        self.assertIn("is_illiterate", validate_inputs({"is_illiterate": "yes"}))

    def test_cleared_fields_remain_cleared_after_validation_error(self):
        applicant = Applicant(suffix="Jr.", is_indigenous=True, is_illiterate=True)
        html = render_to_string("components/profile_personal_fields.html", {
            "applicant": applicant, "form_data": {"profile_details_provided": "1", "suffix": ""}})
        self.assertNotIn("selected", html)
        self.assertNotIn("checked", html)


@override_settings(STORAGES={
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
})
class ProfileSubmissionTests(TestCase):
    def setUp(self):
        self.barangay = Barangay.objects.create(name="Profile Test Barangay")
        self.destination = Barangay.objects.create(name="Destination Barangay")
        self.admin = get_user_model().objects.create_superuser(username="profileadmin", password="test-password")

    def personal_data(self):
        return {
            "firstname": "Juan", "lastname": "Cruz", "middlename": "", "email": "",
            "birthdate": "2000-01-02", "age": "26", "sex": "Male", "civil_status": "Single",
            "brgy": str(self.barangay.pk), "brgy_id": str(self.barangay.pk), "birthplace": "Pio Duran",
            "municipality": "Pio Duran", "province": "Albay", "phone": "09171234567",
            "father": "Pedro Cruz", "mother": "Maria Cruz", "pwd_status": "HEARING", "citizenship_status": "BY_BIRTH",
        }

    def make_applicant(self):
        data = self.personal_data()
        data.pop("brgy_id")
        data.pop("brgy")
        data.update(brgy=self.barangay, birthdate=date(2000, 1, 2), age=26, email=None, is_active=False,
                    suffix="Sr.", is_indigenous=True)
        applicant = Applicant.objects.create(**data)
        applicant.photo.save("old.png", photo())
        applicant.valid_id_document.save("original.pdf", SimpleUploadedFile("original.pdf", b"%PDF-1.7 document"))
        return applicant

    def profile_data(self):
        return {"profile_details_provided": "1", "suffix": "Jr.", "is_illiterate": "on", "photo": photo()}

    def test_new_registration_saves_profile_and_keeps_pwd(self):
        data = {**self.personal_data(), **self.profile_data(),
                "valid_id_document": SimpleUploadedFile("id.pdf", b"%PDF-1.7 document")}
        response = self.client.post(reverse("new-registration"), data)
        self.assertEqual(response.status_code, 302)
        applicant = Applicant.objects.get()
        self.assertEqual(applicant.suffix, "Jr.")
        self.assertTrue(applicant.is_illiterate)
        self.assertFalse(applicant.is_indigenous)
        self.assertEqual(applicant.pwd_status, "HEARING")
        self.assertTrue(applicant.photo.storage.exists(applicant.photo.name))
        self.assertContains(self.client.get(response.url), "Jr.")

    def test_mobile_api_detects_duplicate_without_separate_verification(self):
        from api.views import new_registration_api
        self.make_applicant()
        data = self.personal_data()
        data.update(firstname="juan", lastname="cruz")
        response = new_registration_api(RequestFactory().post(
            "/api/new-registration/", json.dumps(data), content_type="application/json"))
        self.assertEqual(response.status_code, 400)
        self.assertIn("full name and birthdate already exists", json.loads(response.content)["error"])
        self.assertEqual(Applicant.objects.count(), 1)

    def test_offline_registration_retry_returns_same_reference_without_duplicate(self):
        from api.views import new_registration_api
        from Applicants.models import MobileSubmissionReceipt
        reference = "NEWREGISTRATION-1700000000000-unique-request"
        def submit():
            data = {**self.personal_data(), **self.profile_data(), "client_reference": reference,
                    "valid_id_document": SimpleUploadedFile("id.pdf", b"%PDF-1.7 document")}
            return new_registration_api(RequestFactory().post("/api/new-registration/", data))
        first = submit()
        second = submit()
        self.assertEqual(first.status_code, 201, first.content)
        self.assertEqual(second.status_code, 201, second.content)
        self.assertEqual(json.loads(first.content), json.loads(second.content))
        self.assertEqual(Applicant.objects.count(), 1)
        self.assertEqual(MobileSubmissionReceipt.objects.count(), 1)

    def test_failed_offline_submission_can_be_corrected_and_retried(self):
        from api.views import new_registration_api
        from Applicants.models import MobileSubmissionReceipt
        data = {**self.personal_data(), "client_reference": "NEWREGISTRATION-1700000000000-correctable"}
        failed = new_registration_api(RequestFactory().post("/api/new-registration/", data))
        self.assertEqual(failed.status_code, 400)
        self.assertFalse(MobileSubmissionReceipt.objects.exists())
        data["valid_id_document"] = SimpleUploadedFile("id.pdf", b"%PDF-1.7 document")
        saved = new_registration_api(RequestFactory().post("/api/new-registration/", data))
        self.assertEqual(saved.status_code, 201, saved.content)
        self.assertEqual(Applicant.objects.count(), 1)

    def test_mobile_reference_lookup_returns_exact_inactive_record(self):
        from api.views import find_applicant
        applicant = self.make_applicant()
        response = find_applicant(RequestFactory().post("/api/applicants/find/", json.dumps({
            "registration_reference": applicant.registration_reference.lower()}), content_type="application/json"))
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)["applicant"]
        self.assertEqual(result["id"], applicant.pk)
        self.assertFalse(result["is_active"])
        self.assertEqual(result["registration_reference"], applicant.registration_reference)

    def test_mobile_reference_lookup_rejects_invalid_and_unknown_reference(self):
        from api.views import find_applicant
        for reference, status in [("bad", 400), ("PD-" + "A" * 32, 404)]:
            response = find_applicant(RequestFactory().post("/api/applicants/find/", json.dumps({
                "registration_reference": reference}), content_type="application/json"))
            self.assertEqual(response.status_code, status)

    def test_mobile_inactive_services_accept_reference_and_optional_middle_name(self):
        from api.views import create_applicant_reactivation_request, create_applicant_reinstatement_request
        for handler, model in [(create_applicant_reactivation_request, ApplicantReactivationRequest),
                               (create_applicant_reinstatement_request, ApplicantReinstatementRequest)]:
            applicant = self.make_applicant()
            data = {"registration_reference": applicant.registration_reference, "lastname": applicant.lastname,
                    "firstname": applicant.firstname, "middlename": "", "birthdate": "2000-01-02",
                    "reason": "Please restore my registration."}
            response = handler(RequestFactory().post("/api/requests/", json.dumps(data), content_type="application/json"))
            self.assertEqual(response.status_code, 201, response.content)
            self.assertTrue(model.objects.filter(applicant=applicant).exists())

    def test_mobile_all_request_types_save_profile_uploads_without_changing_applicant(self):
        from api.views import (create_applicant_update_request, create_applicant_transfer_request,
                               create_applicant_reactivation_request, create_applicant_reinstatement_request)
        cases = [(create_applicant_update_request, ApplicantUpdateRequest, True),
                 (create_applicant_transfer_request, ApplicantTransferRequest, True),
                 (create_applicant_reactivation_request, ApplicantReactivationRequest, False),
                 (create_applicant_reinstatement_request, ApplicantReinstatementRequest, False)]
        for handler, model, active in cases:
            with self.subTest(model=model.__name__):
                applicant = self.make_applicant()
                applicant.is_active = active
                applicant.status = "APPROVED"
                applicant.save()
                old_photo = applicant.photo.name
                data = {**self.personal_data(), **self.profile_data(), "applicant_id": str(applicant.pk),
                        "registration_reference": applicant.registration_reference, "civil_status": "Married",
                        "current_brgy": str(self.barangay.pk), "new_brgy": str(self.destination.pk),
                        "new_municipality": "Pio Duran", "new_province": "Albay",
                        "reason": "Please update my registration details.",
                        "valid_id_document": SimpleUploadedFile("new.pdf", b"%PDF-1.7 new document")}
                response = handler(RequestFactory().post("/api/requests/", data))
                self.assertEqual(response.status_code, 201, response.content)
                application = model.objects.get(applicant=applicant)
                self.assertEqual(application.suffix, "Jr.")
                self.assertTrue(application.is_illiterate)
                self.assertFalse(application.is_indigenous)
                self.assertTrue(application.photo.storage.exists(application.photo.name))
                self.assertNotEqual(application.valid_id_document.name, applicant.valid_id_document.name)
                applicant.refresh_from_db()
                self.assertEqual(applicant.suffix, "Sr.")
                self.assertEqual(applicant.photo.name, old_photo)

    def test_mobile_request_reuses_existing_document_and_photo(self):
        from api.views import create_applicant_reactivation_request
        applicant = self.make_applicant()
        data = {"registration_reference": applicant.registration_reference, "lastname": applicant.lastname,
                "firstname": applicant.firstname, "middlename": "", "birthdate": "2000-01-02",
                "reason": "Please restore my registration.", "profile_details_provided": "1", "suffix": ""}
        response = create_applicant_reactivation_request(RequestFactory().post("/api/requests/", data))
        self.assertEqual(response.status_code, 201, response.content)
        application = ApplicantReactivationRequest.objects.get()
        self.assertEqual(application.photo.name, applicant.photo.name)
        self.assertEqual(application.valid_id_document.name, applicant.valid_id_document.name)

    def test_web_submission_rejects_duplicate_name_and_birthdate_without_email(self):
        self.make_applicant()
        data = {**self.personal_data(), "firstname": "juan", "lastname": "cruz",
                "valid_id_document": SimpleUploadedFile("id.pdf", b"%PDF-1.7 document")}
        response = self.client.post(reverse("new-registration"), data)
        self.assertContains(response, "full name and birthdate already exists")
        self.assertEqual(Applicant.objects.count(), 1)
        self.assertContains(response, 'value="juan"')

    def test_web_submission_allows_same_name_with_different_birthdate(self):
        self.make_applicant()
        data = {**self.personal_data(), "birthdate": "2001-01-02",
                "valid_id_document": SimpleUploadedFile("id.pdf", b"%PDF-1.7 document")}
        response = self.client.post(reverse("new-registration"), data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Applicant.objects.count(), 2)

    def test_mobile_multipart_registration_saves_web_profile_fields_and_uploads(self):
        from api.views import new_registration_api
        data = {**self.personal_data(), **self.profile_data(), "civil_status": "Married",
                "valid_id_document": SimpleUploadedFile("id.pdf", b"%PDF-1.7 document")}
        response = new_registration_api(RequestFactory().post("/api/new-registration/", data))
        self.assertEqual(response.status_code, 201, response.content)
        applicant = Applicant.objects.get()
        self.assertEqual(applicant.suffix, "Jr.")
        self.assertEqual(applicant.civil_status, "Married")
        self.assertEqual(applicant.middlename, "")
        self.assertIsNone(applicant.email)
        self.assertTrue(applicant.is_illiterate)
        self.assertFalse(applicant.is_indigenous)
        self.assertTrue(applicant.photo.storage.exists(applicant.photo.name))
        self.assertTrue(applicant.valid_id_document.storage.exists(applicant.valid_id_document.name))

    def test_mobile_multipart_requires_document_and_validates_photo_and_suffix(self):
        from api.views import new_registration_api
        for extra in [{}, {"suffix": "VI"}, {"photo": SimpleUploadedFile("fake.png", b"not an image")}]:
            data = {**self.personal_data(), **extra}
            response = new_registration_api(RequestFactory().post("/api/new-registration/", data))
            self.assertEqual(response.status_code, 400, response.content)
            self.assertFalse(Applicant.objects.exists())

    def test_mobile_api_accepts_same_name_with_different_birthdate(self):
        from api.views import new_registration_api
        self.make_applicant()
        data = self.personal_data()
        data["birthdate"] = "2001-01-02"
        response = new_registration_api(RequestFactory().post(
            "/api/new-registration/", json.dumps(data), content_type="application/json"))
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(Applicant.objects.count(), 2)

    @patch("core.views.send_approval_sms")
    @patch("core.views.assign_office_appointment")
    def test_all_requests_keep_profile_pending_until_approval(self, appointment, sms):
        cases = [
            ("update", "update-registration", "submit_update", ApplicantUpdateRequest),
            ("transfer", "transfer-registration", "submit_transfer", ApplicantTransferRequest),
            ("reactivation", "reactivation-registration", "submit_reactivation", ApplicantReactivationRequest),
            ("reinstatement", "reinstatement-registration", "submit_reinstatement", ApplicantReinstatementRequest),
        ]
        for kind, url, action, model in cases:
            with self.subTest(kind=kind):
                self.client.logout()
                applicant = self.make_applicant()
                old_photo = applicant.photo.name
                data = {**self.personal_data(), **self.profile_data(), "action": action,
                        "applicant_id": str(applicant.pk), "reason": "Please update my registration.",
                        "new_brgy": str(self.destination.pk), "new_municipality": "Pio Duran", "new_province": "Albay"}
                if kind == "update":
                    data.update(sex="MALE", civil_status="SINGLE")
                response = self.client.post(reverse(url), data)
                self.assertEqual(response.status_code, 302, response.context.get("error") if response.context else None)
                application = model.objects.get(applicant=applicant)
                self.assertEqual(application.suffix, "Jr.")
                self.assertTrue(application.is_illiterate)
                self.assertFalse(application.is_indigenous)
                applicant.refresh_from_db()
                self.assertEqual(applicant.suffix, "Sr.")
                self.assertEqual(applicant.photo.name, old_photo)
                self.assertFalse(applicant.is_illiterate)
                self.client.force_login(self.admin)
                detail_url = reverse(f"admin-application-{kind}-detail", args=[application.pk])
                self.assertContains(self.client.get(detail_url), "Jr.")
                response = self.client.post(reverse("admin-application-action", args=[kind, application.pk, "approve"]))
                self.assertEqual(response.status_code, 302)
                applicant.refresh_from_db()
                self.assertEqual(applicant.suffix, "Jr.")
                self.assertTrue(applicant.is_illiterate)
                self.assertFalse(applicant.is_indigenous)
                self.assertEqual(applicant.photo.name, application.photo.name)
                self.assertEqual(applicant.pwd_status, "HEARING")

    def test_empty_upload_keeps_photo_and_unchecked_flags_can_be_saved(self):
        applicant = self.make_applicant()
        data = {"action": "submit_reactivation", "applicant_id": applicant.pk,
                "reason": "Please reactivate my registration.", "profile_details_provided": "1", "suffix": ""}
        response = self.client.post(reverse("reactivation-registration"), data)
        self.assertEqual(response.status_code, 302)
        application = ApplicantReactivationRequest.objects.get()
        self.assertEqual(application.photo.name, applicant.photo.name)
        self.assertEqual(application.suffix, "")
        self.assertFalse(application.is_indigenous)

    def test_old_requests_do_not_clear_existing_profile(self):
        from Applicants.profile_details import apply_profile_details
        applicant = self.make_applicant()
        application = ApplicantReactivationRequest.objects.create(applicant=applicant, reason="Legacy request")
        apply_profile_details(application, applicant)
        self.assertEqual(applicant.suffix, "Sr.")
        self.assertTrue(applicant.is_indigenous)
        self.assertTrue(applicant.photo)

    def test_invalid_photo_preserves_submitted_fields(self):
        applicant = self.make_applicant()
        response = self.client.post(reverse("reactivation-registration"), {
            "action": "submit_reactivation", "applicant_id": applicant.pk,
            "reason": "Please reactivate my registration.", **self.profile_data(),
            "photo": SimpleUploadedFile("bad.png", b"not an image"),
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Upload a valid JPG or PNG image.")
        self.assertContains(response, 'value="Jr." selected')
        self.assertRegex(response.content.decode(), r'id="is_illiterate"[^>]*checked')
        self.assertFalse(ApplicantReactivationRequest.objects.exists())
