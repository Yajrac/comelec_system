"""Office visit window: the applicant may come any open office day for N days after approval."""
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

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


def lead_days():
    """Open office days in the visit window (OFFICE_VISIT_LEAD_DAYS, default 3)."""
    return max(1, int(getattr(settings, "OFFICE_VISIT_LEAD_DAYS", 3)))


def _office_holidays(start, end):
    from .models import OfficeHoliday
    return set(OfficeHoliday.objects.filter(date__gte=start, date__lte=end).values_list("date", flat=True))


def visit_window_from(approved_on):
    """(first, last) open office days the applicant may visit, starting the day after approval."""
    holidays = _office_holidays(approved_on, approved_on + timedelta(days=60))
    day, open_days = approved_on, []
    while len(open_days) < lead_days():
        day += timedelta(days=1)
        if not is_office_closed(day, holidays):
            open_days.append(day)
    return open_days[0], open_days[-1]


def visit_window(applicant):
    """(first, last) visit days for an approved applicant, or None. The last day is stored."""
    last = applicant.office_visit_date
    if not last:
        return None
    holidays = _office_holidays(last - timedelta(days=60), last)
    day, counted = last, 1
    while counted < lead_days():
        day -= timedelta(days=1)
        if not is_office_closed(day, holidays):
            counted += 1
    return day, last


def visit_overdue(applicant):
    return bool(applicant.office_visit_date) and timezone.localdate() > applicant.office_visit_date


def format_window(first, last):
    """'Nov 17 to Nov 19, 2026', or 'Dec 29, 2026 to Jan 04, 2027' across years."""
    start = f"{first:%b %d}" if first.year == last.year else f"{first:%b %d, %Y}"
    return f"{start} to {last:%b %d, %Y}" if first != last else f"{last:%b %d, %Y}"


def assign_office_appointment(applicant):
    """Store the last day of the visit window; no daily limit, any open day in the window works."""
    first, last = visit_window_from(timezone.localdate())
    applicant.office_visit_date = last
    applicant.office_visit_slot = None
    applicant.save(update_fields=["office_visit_date", "office_visit_slot"])
    return first, last
