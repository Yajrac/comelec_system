"""Office visit scheduling: the first open office day after approval, with a daily limit."""
from datetime import timedelta

from django.utils import timezone

OFFICE_DAILY_CAPACITY = 50

# Regular holidays with fixed dates (Republic Act No. 9492 and amendments). Holidays whose dates
# change every year (Holy Week, Eid, National Heroes Day, special days) and local holidays are
# added by the office as OfficeHoliday records.
FIXED_HOLIDAYS = {
    (1, 1): "New Year's Day",
    (4, 9): "Araw ng Kagitingan",
    (5, 1): "Labor Day",
    (6, 12): "Independence Day",
    (11, 30): "Bonifacio Day",
    (12, 25): "Christmas Day",
    (12, 30): "Rizal Day",
}


def is_office_closed(day, extra_holidays=frozenset()):
    return day.weekday() >= 5 or (day.month, day.day) in FIXED_HOLIDAYS or day in extra_holidays


def assign_office_appointment(applicant):
    """Schedule the visit on the first open office day after today that still has a free slot."""
    from Applicants.models import Applicant
    from .models import OfficeHoliday

    today = timezone.localdate()
    holidays = set(OfficeHoliday.objects.filter(date__gt=today).values_list("date", flat=True))
    day = today + timedelta(days=1)  # never the same day: approval may come late in the afternoon
    while True:
        if is_office_closed(day, holidays):
            day += timedelta(days=1)
            continue
        scheduled = Applicant.objects.filter(office_visit_date=day).count()
        if scheduled < OFFICE_DAILY_CAPACITY:
            applicant.office_visit_date = day
            applicant.office_visit_slot = scheduled + 1
            applicant.save(update_fields=["office_visit_date", "office_visit_slot"])
            return day, scheduled + 1
        day += timedelta(days=1)
