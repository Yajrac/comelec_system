"""Shared validation for public web forms and mobile API requests."""
import json
import re
import unicodedata
from datetime import date
from functools import wraps
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from .profile_details import SUFFIX_CHOICES, validate_photo

NAME_FIELDS = {"firstname", "lastname", "middlename", "father", "mother"}
LABELS = {"firstname": "First name", "lastname": "Last name", "middlename": "Middle name", "father": "Father's name", "mother": "Mother's name"}


def name_is_valid(value):
    return (any(c.isalpha() for c in value)
            and all(c.isalpha() or unicodedata.category(c).startswith("M")
                    or c in " -'.\u2019" for c in value))


def validate_inputs(data, files=None):
    errors = {}
    for key, raw in data.items():
        if key in {"csrfmiddlewaretoken", "action"}:
            continue
        if key == "suffix":
            if not isinstance(raw, str) or raw.strip() not in {"", *dict(SUFFIX_CHOICES)}:
                errors[key] = "Select a valid suffix."
        elif key in {"is_indigenous", "is_illiterate"}:
            if raw != "on":
                errors[key] = "Select a valid checkbox value."
        elif key in NAME_FIELDS:
            if not isinstance(raw, str):
                errors[key] = "Enter a valid name."
                continue
            value = raw.strip()
            if key in {"middlename", "father", "mother"} and not value:
                continue
            if len(value) > 255 or not name_is_valid(value):
                errors[key] = LABELS[key] + " must contain letters, spaces, hyphens, apostrophes, or periods only (maximum 255 characters)."
        elif key == "phone" and not re.fullmatch(r"09[0-9]{9}", str(raw).strip()):
            errors[key] = "Enter an 11-digit Philippine mobile number starting with 09."
        elif key == "email":
            if isinstance(raw, str) and not raw.strip():
                continue
            try:
                if not isinstance(raw, str) or len(raw.strip()) > 254:
                    raise ValidationError("Invalid email")
                validate_email(raw.strip())
            except ValidationError:
                errors[key] = "Enter a valid email address (maximum 254 characters)."
        elif key == "birthdate":
            try:
                born = date.fromisoformat(str(raw))
                if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", str(raw)) or born >= timezone.localdate():
                    raise ValueError()
            except (ValueError, TypeError):
                errors[key] = "Enter a valid birthdate earlier than today."
        elif key == "age":
            if isinstance(raw, bool) or not re.fullmatch(r"[0-9]{1,3}", str(raw)) or not 1 <= int(raw) <= 150:
                errors[key] = "Enter a whole-number age between 1 and 150."
        elif key in {"brgy", "brgy_id", "new_brgy", "new_brgy_id", "applicant_id"}:
            if not re.fullmatch(r"[0-9]{1,10}", str(raw)) or int(raw) < 1:
                errors[key] = "Select a valid record."
        elif key in {"birthplace", "province", "municipality", "new_province", "new_municipality"}:
            if not isinstance(raw, str) or not raw.strip() or len(raw.strip()) > 255 or any(unicodedata.category(c) == "Cc" for c in raw):
                errors[key] = "Enter a valid value (maximum 255 characters)."
        elif key == "reason":
            if not isinstance(raw, str) or not raw.strip() or len(raw) > 5000:
                errors[key] = "Enter a reason (maximum 5,000 characters)."
        elif key == "registration_reference":
            if not re.fullmatch(r"PD-[A-F0-9]{32}", str(raw).strip().upper()):
                errors[key] = "Enter PD- followed by exactly 32 hexadecimal characters."
        elif key in {"sex", "civil_status", "pwd_status", "citizenship_status"}:
            choices = {
                "sex": {"MALE", "FEMALE"},
                "civil_status": {"SINGLE", "MARRIED", "WIDOWED", "SEPARATED"},
                "pwd_status": {"NO", "VISUAL", "HEARING", "PHYSICAL", "INTELLECTUAL", "PSYCHOSOCIAL", "MULTIPLE", "OTHER"},
                "citizenship_status": {"BY_BIRTH", "NATURALIZED"},
            }
            if not isinstance(raw, str) or raw.upper() not in choices[key]:
                errors[key] = "Select a valid option."
    if "age" in data and "birthdate" in data and not ({"age", "birthdate"} & errors.keys()):
        born = date.fromisoformat(str(data["birthdate"]))
        today = timezone.localdate()
        expected = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        if int(data["age"]) != expected:
            errors["age"] = "Age must match the date of birth."
    for key, upload in (files or {}).items():
        if key == "photo":
            try:
                validate_photo(upload)
            except ValidationError as error:
                errors[key] = error.messages[0]
            continue
        if upload.size > 5 * 1024 * 1024:
            errors[key] = "File must be 5 MB or smaller."
        elif Path(upload.name).suffix.lower() not in {".pdf", ".png", ".jpg", ".jpeg"}:
            errors[key] = "Upload a PDF, PNG, or JPEG file."
        else:
            position = upload.tell()
            header = upload.read(8)
            upload.seek(position)
            suffix = Path(upload.name).suffix.lower()
            valid = (header.startswith(b"%PDF-") if suffix == ".pdf" else header.startswith(b"\x89PNG\r\n\x1a\n") if suffix == ".png" else header.startswith(b"\xff\xd8\xff"))
            if not valid:
                errors[key] = "File contents do not match the selected file type."
    return errors


def validate_request(template=None, api=False):
    def decorate(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if request.method != "POST":
                return view(request, *args, **kwargs)
            if api and request.content_type == "application/json":
                try:
                    data = json.loads(request.body)
                except (ValueError, UnicodeDecodeError):
                    return JsonResponse({"success": False, "error": "Invalid JSON data."}, status=400)
                if not isinstance(data, dict):
                    return JsonResponse({"success": False, "error": "Expected a JSON object."}, status=400)
            else:
                data = request.POST
            if "birthdate" in data and view.__name__ in {"new_registration", "update_registration", "new_registration_api", "create_applicant_update_request"}:
                try:
                    born = date.fromisoformat(str(data["birthdate"]))
                    today = timezone.localdate()
                    age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
                    data = data.copy()
                    data["age"] = str(age)
                    if api and request.content_type == "application/json":
                        request._body = json.dumps(data).encode("utf-8")
                    else:
                        request.POST = data
                except (ValueError, TypeError):
                    pass
            errors = validate_inputs(data, request.FILES)
            if api and data.get("profile_details_provided") == "1" and view.__name__ in {
                "create_applicant_update_request", "create_applicant_transfer_request",
                "create_applicant_reactivation_request", "create_applicant_reinstatement_request",
            }:
                reason = data.get("reason", "")
                if not isinstance(reason, str) or not 5 <= len(reason.strip()) <= 2000:
                    errors["reason"] = "Provide a reason between 5 and 2,000 characters."
            if "birthdate" in data and "birthdate" not in errors and view.__name__ in {"new_registration", "update_registration", "new_registration_api", "create_applicant_update_request"}:
                from .eligibility import age_eligibility, election_date
                if not age_eligibility(date.fromisoformat(str(data["birthdate"])))['eligible']:
                    errors['birthdate'] = f"You must be at least 15 years old on election day ({election_date():%B %d, %Y}) to apply for SK registration."

            if not errors:
                return view(request, *args, **kwargs)
            message = next(iter(errors.values()))
            if api:
                return JsonResponse({"success": False, "error": message, "message": message, "errors": errors}, status=400)
            from .models import Applicant, Barangay
            applicant = None
            pk = str(data.get("applicant_id", ""))
            if pk.isdigit() and len(pk) <= 10:
                applicant = Applicant.objects.filter(pk=int(pk)).first()
            return render(request, template, {"error": message, "field_errors": errors,
                "form_data": data, "search_data": data, "applicant": applicant,
                "barangays": Barangay.objects.order_by("name"), "pwd_choices": Applicant.PWD_CHOICES})
        return wrapped
    return decorate
