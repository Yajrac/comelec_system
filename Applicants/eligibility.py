from datetime import date
from django.conf import settings


def election_date():
    value = settings.VOTER_ELECTION_DATE
    return value if isinstance(value, date) else date.fromisoformat(value)


def age_on(born, target):
    return target.year - born.year - ((target.month, target.day) < (born.month, born.day))


def age_eligibility(born):
    age = age_on(born, election_date())
    return {"age": age, "eligible": age >= 15, "sk": 15 <= age <= 30, "regular": age >= 18}
