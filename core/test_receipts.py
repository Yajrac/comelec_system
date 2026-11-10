from datetime import date
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from Applicants.models import Applicant, ApplicantBiometric, AcknowledgmentReceipt

@override_settings(STORAGES={"default": {"BACKEND": "django.core.files.storage.FileSystemStorage"}, "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}})
class ReceiptTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(username="receiptadmin", password="test-password")
        self.applicant = Applicant.objects.create(lastname="DELA CRUZ", firstname="JUAN", middlename="SANTOS", age=25, sex="Male", birthdate=date(2000,1,1), birthplace="Albay", phone="09123456789", verification_status="VERIFIED")
        self.bio = ApplicantBiometric.objects.create(applicant=self.applicant, completed=True, biometrics_completed=True)
        self.url = reverse("acknowledgment-receipt", args=[self.applicant.pk])

    def test_anonymous_cannot_issue(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)
        self.assertFalse(AcknowledgmentReceipt.objects.exists())

    @patch("core.receipts.capture_complete", return_value=True)
    def test_officer_settings_update_existing_receipt_without_changing_number(self, capture):
        from core.models import ReceiptSettings
        url = reverse('receipt-settings', args=[self.applicant.pk])
        self.assertEqual(self.client.post(url, {'officer_name': 'Unauthorized'}).status_code, 302)
        self.assertFalse(ReceiptSettings.objects.exists())
        self.client.force_login(self.admin)
        self.client.get(self.url)
        number = AcknowledgmentReceipt.objects.get(applicant=self.applicant).application_number
        self.assertEqual(self.client.post(url, {'officer_name': 'Maria Santos'}).status_code, 302)
        response = self.client.get(self.url)
        self.assertEqual(response.context['receipt_values']['officer'], 'Maria Santos')
        self.assertContains(response, 'Receipt Settings')
        self.assertEqual(AcknowledgmentReceipt.objects.get(applicant=self.applicant).application_number, number)
        self.client.post(url, {'officer_name': 'x' * 101})
        self.assertEqual(ReceiptSettings.objects.get(pk=1).officer_name, 'Maria Santos')
        self.client.post(url, {'officer_name': ''})
        self.assertEqual(self.client.get(self.url).context['receipt_values']['officer'], '')

    @patch("core.receipts.capture_complete", return_value=False)
    def test_missing_physical_capture_blocks_receipt(self, capture):
        self.client.force_login(self.admin)
        self.assertRedirects(self.client.get(self.url), reverse("admin-applicant-biometric", args=[self.applicant.pk]), fetch_redirect_response=False)
        self.assertFalse(AcknowledgmentReceipt.objects.exists())

    @patch("core.receipts.capture_complete", return_value=True)
    def test_receipt_is_stable_and_pdf_ignores_query_tampering(self, capture):
        self.client.force_login(self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "SAMPLE ONLY")
        receipt = AcknowledgmentReceipt.objects.get(applicant=self.applicant)
        self.assertRegex(receipt.application_number, r"^[0-9]{12}$")
        self.applicant.lastname = "CHANGED"
        self.applicant.save()
        pdf = self.client.get(self.url, {"format":"pdf", "application_no":"123", "lastname":"FORGED"})
        self.assertEqual(pdf.status_code, 200)
        self.assertTrue(pdf.content.startswith(b"%PDF"))
        receipt.refresh_from_db()
        self.assertEqual(receipt.details["lastname"], "DELA CRUZ")
        self.assertEqual(AcknowledgmentReceipt.objects.count(), 1)
        self.assertContains(self.client.get(self.url), receipt.application_number)

    @patch("core.receipts.capture_complete", return_value=True)
    @patch("core.views.capture_complete", return_value=True)
    def test_print_slip_uses_compact_receipt_and_preserves_long_names(self, view_capture, receipt_capture):
        self.client.force_login(self.admin)
        self.applicant.lastname = 'A VERY LONG FAMILY NAME THAT EXCEEDS TWENTY EIGHT'
        self.applicant.save()
        response = self.client.get(reverse('print-slip-account', args=[self.applicant.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'comelec/applications/acknowledgment_receipt.html')
        self.assertEqual(''.join(response.context['name_rows'][0]['letters']).strip(), self.applicant.lastname)
        self.assertContains(response, 'Date of ERB Hearing:')
        self.assertContains(response, 'Download PDF')
        self.assertEqual(sum(option['selected'] for option in response.context['application_options']), 1)
