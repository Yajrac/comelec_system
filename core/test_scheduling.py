"""Office visit window: any open office day for 3 days after approval, weekends and holidays skipped."""
from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from Applicants.models import Applicant, ApplicantBiometric
from core.models import OfficeHoliday
from core.scheduling import assign_office_appointment, format_window, visit_window


class OfficeVisitWindowTests(TestCase):
    def applicant(self, name='Juan'):
        return Applicant.objects.create(lastname='Cruz', firstname=name, middlename='', age=30, sex='Male',
                                        birthdate=date(1996, 1, 2), birthplace='X', phone='09171234567')

    def schedule(self, approved_on):
        with patch('core.scheduling.timezone.localdate', return_value=approved_on):
            return assign_office_appointment(self.applicant())

    def test_window_is_the_next_three_working_days(self):
        self.assertEqual(self.schedule(date(2026, 11, 16)), (date(2026, 11, 17), date(2026, 11, 19)))  # Mon: Tue-Thu
        self.assertEqual(self.schedule(date(2026, 11, 20)), (date(2026, 11, 23), date(2026, 11, 25)))  # Fri: Mon-Wed
        self.assertEqual(self.schedule(date(2026, 11, 21)), (date(2026, 11, 23), date(2026, 11, 25)))  # Sat: Mon-Wed

    def test_holidays_are_not_counted(self):
        # Thu Nov 26: Fri 27, (Mon 30 Bonifacio Day), Tue Dec 1, Wed Dec 2.
        self.assertEqual(self.schedule(date(2026, 11, 26)), (date(2026, 11, 27), date(2026, 12, 2)))
        OfficeHoliday.objects.create(date=date(2026, 12, 8), name='Feast of the Immaculate Conception')
        self.assertEqual(self.schedule(date(2026, 12, 7)), (date(2026, 12, 9), date(2026, 12, 11)))

    def test_no_daily_limit_and_stored_window_round_trips(self):
        windows = {self.schedule(date(2026, 11, 16)) for _ in range(60)}
        self.assertEqual(windows, {(date(2026, 11, 17), date(2026, 11, 19))})
        applicant = Applicant.objects.last()
        self.assertEqual(applicant.office_visit_date, date(2026, 11, 19))
        self.assertIsNone(applicant.office_visit_slot)
        self.assertEqual(visit_window(applicant), (date(2026, 11, 17), date(2026, 11, 19)))

    def test_window_length_setting_and_formatting(self):
        with self.settings(OFFICE_VISIT_LEAD_DAYS=1):
            self.assertEqual(self.schedule(date(2026, 11, 16)), (date(2026, 11, 17), date(2026, 11, 17)))
        self.assertEqual(format_window(date(2026, 11, 17), date(2026, 11, 19)), 'Nov 17 to Nov 19, 2026')
        self.assertEqual(format_window(date(2026, 12, 29), date(2027, 1, 4)), 'Dec 29, 2026 to Jan 04, 2027')

    @override_settings(PAGE_RATE_LIMIT_REQUESTS=0, STORAGES={'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'},
                       'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
    def test_admin_sees_the_window_and_overdue_mark(self):
        applicant = self.applicant()
        applicant.office_visit_date = date(2026, 11, 19)
        applicant.save()
        ApplicantBiometric.objects.create(applicant=applicant)
        self.client.force_login(get_user_model().objects.create_superuser(username='windowadmin', password='x'))
        with patch('core.scheduling.timezone.localdate', return_value=date(2026, 11, 18)):
            page = self.client.get(reverse('admin-applicant-biometric', args=[applicant.pk]))
        self.assertContains(page, 'Office visit window: Nov 17 to Nov 19, 2026')
        self.assertNotContains(page, 'window has passed')
        with patch('core.scheduling.timezone.localdate', return_value=date(2026, 11, 20)):
            page = self.client.get(reverse('admin-applicant-biometric', args=[applicant.pk]))
        self.assertContains(page, 'window has passed')
