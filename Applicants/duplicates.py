"""Duplicate registration check: "certain" and "possible" matches on name and birthdate.

Names are compared in one normal form: uppercase, accents removed (Ñ -> N), punctuation
and spacing ignored, "Ma." read as "Maria". Only applicants with the same birthdate are
compared, so the check stays fast as the number of applicants grows.

certain  - same last, first and middle name (or both without a middle name)
possible - same last name, first given name and birthdate, but the middle name is blank
           or only an initial on one side, or one has an extra given name
"""
import re
import unicodedata

CERTAIN, POSSIBLE = "certain", "possible"
SUFFIXES = {"JR", "SR", "II", "III", "IV", "V"}
ABBREVIATIONS = {"MA": "MARIA", "STA": "SANTA", "STO": "SANTO"}


def name_tokens(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).upper()
    tokens = re.sub(r"[^A-Z]+", " ", text).split()
    return [ABBREVIATIONS.get(token, token) for token in tokens if token not in SUFFIXES]


def compact(value):
    """One string without spaces: "Dela Cruz" and "DelaCruz" are the same."""
    return "".join(name_tokens(value))


def tidy(value):
    """Name as stored: surrounding spaces removed and inner spaces collapsed (case kept)."""
    return " ".join(str(value or "").split())


def match_level(existing, lastname, firstname, middlename):
    """CERTAIN, POSSIBLE or None for one existing applicant with the same birthdate."""
    if compact(existing.lastname) != compact(lastname):
        return None
    old_first, new_first = name_tokens(existing.firstname), name_tokens(firstname)
    if not old_first or not new_first or old_first[0] != new_first[0]:
        return None
    old_middle, new_middle = compact(existing.middlename), compact(middlename)
    same_first = "".join(old_first) == "".join(new_first)
    if same_first and old_middle == new_middle:
        return CERTAIN
    shorter, longer = sorted((old_first, new_first), key=len)
    first_compatible = same_first or set(shorter) <= set(longer)
    middle_compatible = (not old_middle or not new_middle or old_middle == new_middle
                         or (min(len(old_middle), len(new_middle)) == 1 and old_middle[0] == new_middle[0]))
    return POSSIBLE if first_compatible and middle_compatible else None


def find_duplicate(lastname, firstname, middlename, birthdate, exclude_pk=None):
    """(level, applicant) for the earliest certain match, else the earliest possible one."""
    from .models import Applicant

    if not birthdate:
        return None, None
    candidates = Applicant.objects.filter(birthdate=birthdate).order_by("id")
    if exclude_pk:
        candidates = candidates.exclude(pk=exclude_pk)
    possible = None
    for applicant in candidates:
        level = match_level(applicant, lastname, firstname, middlename)
        if level == CERTAIN:
            return CERTAIN, applicant
        if level == POSSIBLE and possible is None:
            possible = applicant
    return (POSSIBLE, possible) if possible else (None, None)
