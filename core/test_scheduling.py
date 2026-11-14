"""Office visit date: the next open office day after approval, skipping weekends and holidays."""
from datetime import date
from unittest.mock import patch

from django.test import TestCase

from Applicants.models import Applicant
from core.models import OfficeHoliday
from core.scheduling import OFFICE_DAILY_CAPACITY, assign_office_appointment


class OfficeScheduleTests(TestCase):
    def applicant(self, name='Juan'):
        return Applicant.objects.create(lastname='Cruz', firstname=name, middlename='', age=30, sex='Male',
                                        birthdate=date(1996, 1, 2), birthplace='X', phone='09171234567')

    def schedule(self, approved_on):
        with patch('core.scheduling.timezone.localdate', return_value=approved_on):
            return assign_office_appointment(self.applicant())

    def test_next_working_day_never_the_same_day(self):
        self.assertEqual(self.schedule(date(2026, 11, 16))[0], date(2026, 11, 17))  # Monday -> Tuesday
        self.assertEqual(self.schedule(date(2026, 11, 20))[0], date(2026, 11, 23))  # Friday -> Monday
        self.assertEqual(self.schedule(date(2026, 11, 21))[0], date(2026, 11, 23))  # Saturday -> Monday

    def test_fixed_and_office_holidays_are_skipped(self):
        # Friday Nov 27 -> Monday Nov 30 is Bonifacio Day -> Tuesday Dec 1.
        self.assertEqual(self.schedule(date(2026, 11, 27))[0], date(2026, 12, 1))
        OfficeHoliday.objects.create(date=date(2026, 12, 8), name='Feast of the Immaculate Conception')
        self.assertEqual(self.schedule(date(2026, 12, 7))[0], date(2026, 12, 9))
        # Dec 24 (Thu) -> Dec 25 holiday, weekend, Dec 28 (Mon).
        self.assertEqual(self.schedule(date(2026, 12, 24))[0], date(2026, 12, 28))

    def test_full_day_moves_to_the_next_open_day_and_slots_count_up(self):
        Applicant.objects.bulk_create([
            Applicant(lastname='Full', firstname=str(i), middlename='', age=30, sex='Male', birthdate=date(1996, 1, 2),
                      birthplace='X', phone='09171234567', office_visit_date=date(2026, 11, 17), office_visit_slot=i + 1,
                      registration_reference=f'PD-{i:032X}')
            for i in range(OFFICE_DAILY_CAPACITY)])
        self.assertEqual(self.schedule(date(2026, 11, 16)), (date(2026, 11, 18), 1))
        self.assertEqual(self.schedule(date(2026, 11, 16)), (date(2026, 11, 18), 2))
