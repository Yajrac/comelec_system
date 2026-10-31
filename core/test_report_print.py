from datetime import date
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from Applicants.models import Applicant, Barangay


@override_settings(STORAGES={"default": {"BACKEND": "django.core.files.storage.InMemoryStorage"}, "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}})
class ReportPrintTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(username="reportadmin", password="test-only-password")
        self.client.force_login(self.admin)
        self.barangay = Barangay.objects.create(name="Caratagan")
        other = Barangay.objects.create(name="Other")
        for index, (name, barangay) in enumerate([("Zulu", self.barangay), ("Alpha", self.barangay), ("Hidden", other)]):
            Applicant.objects.create(lastname=name, firstname="Juan", middlename="", age=26,
                sex="Male", birthdate=date(2000, 1, 2), birthplace="Pio Duran", brgy=barangay,
                email=f"report{index}@example.com", phone="09171234567", father="Pedro", mother="Maria")

    def test_print_ignores_old_filters_and_is_alphabetical(self):
        response = self.client.get(reverse("admin-reports"), {"format": "print", "barangay": self.barangay.pk, "application_type": "NEW"})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "comelec/reports_print.html")
        html = response.content.decode()
        self.assertLess(html.index("ALPHA, JUAN"), html.index("ZULU, JUAN"))
        self.assertIn("HIDDEN, JUAN", html)
        self.assertEqual(response.context["total"], 3)
        self.assertContains(response, "Page 1 of 1")

    def test_old_date_range_does_not_hide_records(self):
        response = self.client.get(reverse("admin-reports"), {"format": "print", "date_to": "1990-01-01"})
        self.assertContains(response, "ALPHA, JUAN")
        self.assertEqual(response.context["total"], 3)

    def test_print_requires_admin(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("admin-reports"), {"format": "print"}).status_code, 302)

    def test_reports_page_shows_all_records_without_barangay_headings(self):
        response = self.client.get(reverse("admin-reports"), {"barangay": self.barangay.pk, "application_type": "NEW"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Applicant's Name")
        self.assertContains(response, "ALPHA, JUAN")
        self.assertContains(response, "HIDDEN, JUAN")
        self.assertNotContains(response, "Barangay: Caratagan")
        rows = response.context["applicant_list_groups"][0]["rows"]
        self.assertEqual([row["number"] for row in rows], [1, 2, 3])

    def test_reports_list_has_print_button_and_verified_print_excludes_unverified(self):
        response = self.client.get(reverse("admin-reports"))
        self.assertContains(response, "Print / Save PDF")
        response = self.client.get(reverse("admin-applicants"), {"format": "print"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "LIST OF VERIFIED APPLICANTS")
        self.assertNotContains(response, "ALPHA, JUAN")
        self.assertEqual(response.context["total"], 0)

    def test_download_pdf_attachment(self):
        response = self.client.get(reverse("admin-reports"), {"format": "pdf"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF-"))
        self.assertIn("attachment;", response["Content-Disposition"])
        self.assertIn("applicant-list-", response["Content-Disposition"])
        self.client.logout()
        self.assertEqual(self.client.get(reverse("admin-reports"), {"format": "pdf"}).status_code, 302)

    def test_year_matches_table_print_and_pdf_and_old_months_are_ignored(self):
        records = list(Applicant.objects.order_by("pk"))
        for record, joined in zip(records, [date(2025, 1, 10), date(2025, 3, 10), date(2025, 2, 10)]):
            Applicant.objects.filter(pk=record.pk).update(date_joined=joined)
        params = {"year": "2025", "months": ["1", "3"]}
        response = self.client.get(reverse("admin-reports"), params)
        self.assertContains(response, "ZULU, JUAN")
        self.assertContains(response, "ALPHA, JUAN")
        self.assertContains(response, "HIDDEN, JUAN")
        self.assertEqual(response.context["total_applications"], 3)
        params["format"] = "print"
        response = self.client.get(reverse("admin-reports"), params)
        self.assertEqual(response.context["total"], 3)
        self.assertContains(response, "Period: 2025")
        params["format"] = "pdf"
        response = self.client.get(reverse("admin-reports"), params)
        self.assertTrue(response.content.startswith(b"%PDF-"))

    def test_invalid_period_values_are_ignored(self):
        response = self.client.get(reverse("admin-reports"), {"year": "bad", "months": ["0", "13", "bad"]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_applications"], 3)

    def test_each_summary_table_has_pdf_download(self):
        for table in ["types", "barangays"]:
            response = self.client.get(reverse("admin-reports"), {"format": "pdf", "table": table})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Content-Type"], "application/pdf")
            self.assertTrue(response.content.startswith(b"%PDF-"))
        response = self.client.get(reverse("admin-reports"))
        self.assertContains(response, "Report tables")
        self.assertContains(response, "report-tables.js")

    def test_summary_print_and_matching_header_controls(self):
        for table, title in [("types", "APPLICATION TYPE REPORT"), ("barangays", "BARANGAY REPORT")]:
            response = self.client.get(reverse("admin-reports"), {"format": "print", "table": table, "year": "2025"})
            self.assertTemplateUsed(response, "comelec/reports_summary_print.html")
            self.assertContains(response, title)
            self.assertContains(response, "Period: 2025")
        response = self.client.get(reverse("admin-reports"))
        self.assertContains(response, 'name="year"', count=5)
        self.assertContains(response, "Print / Save PDF", count=5)

    def test_applicant_list_does_not_repeat_service_requests_and_uses_current_data(self):
        from Applicants.models import ApplicantUpdateRequest, ApplicantTransferRequest, ApplicantReactivationRequest, ApplicantReinstatementRequest
        from unittest.mock import patch
        from django.http import HttpResponse
        applicant = Applicant.objects.get(lastname="Alpha")
        ApplicantUpdateRequest.objects.create(applicant=applicant, lastname="Oldname", firstname="Juan",
            age=26, birthdate=date(2000, 1, 2), brgy=self.barangay)
        ApplicantTransferRequest.objects.create(applicant=applicant, current_brgy=self.barangay,
            new_brgy=Barangay.objects.get(name="Other"))
        ApplicantReactivationRequest.objects.create(applicant=applicant, reason="Test")
        ApplicantReinstatementRequest.objects.create(applicant=applicant, reason="Test")
        page = self.client.get(reverse("admin-reports"))
        rows = page.context["applicant_list_groups"][0]["rows"]
        self.assertEqual(len(rows), 3)
        self.assertEqual(sum(row['name']=='ALPHA, JUAN' for row in rows), 1)
        self.assertEqual(next(row['address'] for row in rows if row['name']=='ALPHA, JUAN'), 'Caratagan, Pio Duran, Albay')
        printed = self.client.get(reverse("admin-reports"), {"format": "print", "table": "applicants"})
        self.assertEqual(printed.context["total"], 3)
        with patch('core.report_pdf.download_applicant_list', return_value=HttpResponse('pdf')) as download:
            self.client.get(reverse("admin-reports"), {"format": "pdf", "table": "applicants"})
            self.assertEqual(download.call_args.args[0], page.context["applicant_list_groups"])

    def test_applicant_list_keeps_different_people_with_same_name(self):
        original = Applicant.objects.get(lastname="Alpha")
        Applicant.objects.create(lastname=original.lastname, firstname=original.firstname, middlename="",
            age=26, birthdate=date(2000, 1, 2), sex="Male", birthplace="Pio Duran", phone="09171234567")
        response = self.client.get(reverse("admin-reports"))
        rows = response.context["applicant_list_groups"][0]["rows"]
        self.assertEqual(len(rows), 4)
        self.assertEqual(sum(row['name']=='ALPHA, JUAN' for row in rows), 2)
