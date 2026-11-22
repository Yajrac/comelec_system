from datetime import date
from django.conf import settings


def election_date():
    value = settings.VOTER_ELECTION_DATE
    return value if isinstance(value, date) else date.fromisoformat(value)


def age_on(born, target):
    return target.year - born.year - ((target.month, target.day) < (born.month, born.day))


def _years_before(day, years):
    try:
        return day.replace(year=day.year - years)
    except ValueError:  # Feb 29 in a non-leap year
        return day.replace(year=day.year - years, day=28)


def is_sk(born):
    """SK Registration: a new registration of someone 15-17 years old on election day."""
    return born is not None and 15 <= age_on(born, election_date()) <= 17


def sk_filter(prefix=""):
    """Database filter for is_sk(): born after the 18th-birthday cut-off and on/before the 15th."""
    from django.db.models import Q
    day = election_date()
    return Q(**{f"{prefix}birthdate__gt": _years_before(day, 18), f"{prefix}birthdate__lte": _years_before(day, 15)})


def age_eligibility(born):
    age = age_on(born, election_date())
    return {"age": age, "eligible": age >= 15, "sk": 15 <= age <= 30, "regular": age >= 18}
