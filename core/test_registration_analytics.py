from datetime import date, datetime
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from Applicants.models import Applicant, ApplicantUpdateRequest
from core.registration_analytics import registration_analytics


@override_settings(PAGE_RATE_LIMIT_REQUESTS=0, STORAGES={"default": {"BACKEND": "django.core.files.storage.InMemoryStorage"}, "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}})
class RegistrationAnalyticsTests(TestCase):
    def make_applicant(self, name, joined, birthdate, sex="Male", pwd="NO"):
        person = Applicant.objects.create(firstname=name, lastname="Cruz", middlename="", age=99,
            birthdate=birthdate, sex=sex, pwd_status=pwd, birthplace="Pio Duran", phone="09171234567",
            email=name+"@example.com", father="Pedro Cruz", mother="Maria Cruz")
        Applicant.objects.filter(pk=person.pk).update(date_joined=joined)
        return person

    @patch("core.registration_analytics.timezone.localdate", return_value=date(2026, 10, 31))
    def test_trends_zero_fill_and_demographics_do_not_double_count_requests(self, today):
        person = self.make_applicant("Juan", date(2025, 1, 2), date(2000, 12, 1), "MALE", "PHYSICAL")
        self.make_applicant("Maria", date(2025, 3, 2), date(1960, 1, 1), "Female")
        self.make_applicant("Previous", date(2024, 1, 1), date(1980, 1, 1))
        update = ApplicantUpdateRequest.objects.create(applicant=person, firstname="Juan", lastname="Cruz", middlename="",
            age=25, sex="Male", birthdate=person.birthdate, birthplace="Pio Duran", phone=person.phone,
            email=person.email, pwd_status="PHYSICAL", citizenship_status="BY_BIRTH", father="Pedro", mother="Maria")
        ApplicantUpdateRequest.objects.filter(pk=update.pk).update(requested_at=timezone.make_aware(datetime(2025, 3, 15, 12)))
        result = registration_analytics(2025)
        self.assertEqual(len(result["trends"]), 12)
        self.assertEqual([row["total"] for row in result["trends"][:3]], [1, 0, 2])
        self.assertEqual(result["trends"][1]["change"], "-1")
        self.assertEqual(result["trends"][2]["change"], "+2")
        self.assertEqual(result["demographic_total"], 2)
        self.assertNotIn("Unknown", result["charts"]["age"]["labels"])
        self.assertEqual(sum(result["charts"]["age"]["values"]), 2)
        for key in ["sex", "pwd"]:
            self.assertEqual(sum(result["charts"][key]["values"]), 2)
        self.assertEqual(result["charts"]["age"]["values"], [0, 0, 1, 0, 0, 1])
        self.assertEqual(result["charts"]["sex"]["values"], [1, 1, 0])
        self.assertEqual(result["charts"]["pwd"]["values"], [1, 1, 0])
        all_years = registration_analytics()
        self.assertEqual([row["period"] for row in all_years["trends"]], ["2024", "2025"])
        self.assertEqual(sum(row["total"] for row in all_years["trends"]), 4)

    def test_empty_year_has_zero_rows_and_unknown_values_are_preserved(self):
        empty = registration_analytics(2020)
        self.assertEqual(len(empty["trends"]), 12)
        self.assertTrue(all(row["total"] == 0 for row in empty["trends"]))
        self.assertEqual(empty["demographic_total"], 0)
        self.make_applicant("Unknown", date(2025, 1, 1), date(2099, 1, 1), "unspecified", "")
        result = registration_analytics(2025)
        self.assertNotIn("Unknown", result["charts"]["age"]["labels"])
        self.assertEqual(sum(result["charts"]["age"]["values"]), 0)
        for key in ["sex", "pwd"]:
            self.assertEqual(result["charts"][key]["values"][-1], 1)

    def test_reports_and_exports_and_dashboard_include_analytics(self):
        user = get_user_model().objects.create_superuser(username="analyticsadmin", password="test-password")
        self.client.force_login(user)
        self.make_applicant("Juan", date(2025, 1, 1), date(2000, 1, 1))
        response = self.client.get(reverse("admin-reports"), {"year": "2025"})
        self.assertContains(response, "Registration Trends")
        self.assertContains(response, "Applicant Demographics")
        self.assertEqual(response.context["registration_analytics"]["demographic_total"], 1)
        for table in ["trends", "demographics"]:
            response = self.client.get(reverse("admin-reports"), {"year": "2025", "format": "print", "table": table})
            self.assertTemplateUsed(response, "comelec/reports_summary_print.html")
            self.assertContains(response, "Period: 2025")
            response = self.client.get(reverse("admin-reports"), {"year": "2025", "format": "pdf", "table": table})
            self.assertEqual(response["Content-Type"], "application/pdf")
            self.assertTrue(response.content.startswith(b"%PDF-"))
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "dashboardTrendsChart")
        for key in ["trends", "age", "sex", "pwd"]:
            self.assertIn(key, response.context["dashboard_chart_data"])

    @patch("core.registration_analytics.timezone.localdate", return_value=date(2026, 11, 1))
    def test_age_groups_separate_under_fifteen_and_fifteen_to_seventeen(self, today):
        self.make_applicant("Young", date(2026, 1, 1), date(2011, 11, 2))
        self.make_applicant("Fifteen", date(2026, 1, 1), date(2011, 11, 1))
        self.make_applicant("Seventeen", date(2026, 1, 1), date(2009, 1, 1))
        self.make_applicant("Eighteen", date(2026, 1, 1), date(2008, 11, 1))
        data = registration_analytics(2026)
        chart = data['charts']['age']
        counts = dict(zip(chart['labels'], chart['values']))
        self.assertEqual(counts['Under 15'], 1)
        self.assertEqual(counts['15\u201317'], 2)
        self.assertEqual(counts['18\u201330'], 1)
