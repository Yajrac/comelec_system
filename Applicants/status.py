"""Public status check by registration reference number (shown on the Home page).

The 32-character random reference is the key, so only a shortened name and the
statuses are shown: no address, birthdate, phone, email or files.
"""
import re

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import Applicant

REFERENCE = re.compile(r"PD-[A-F0-9]{32}")
REQUESTS = (
    ("update_requests", "Correction / Update"),
    ("transfer_requests", "Transfer"),
    ("reactivation_requests", "Reactivation"),
    ("reinstatement_requests", "Reinstatement"),
)
REQUEST_STATUS = {
    "PENDING": ("Pending review", "pending"),
    "REVIEW": ("Under review", "review"),
    "APPROVED": ("Approved", "approved"),
    "DISAPPROVED": ("Disapproved - please visit the office", "disapproved"),
}


def normalize_reference(value):
    """Accept lowercase, spaces and a missing "PD-" prefix."""
    text = re.sub(r"\s+", "", str(value or "")).upper()
    if text and not text.startswith("PD-"):
        text = "PD-" + text.removeprefix("PD")
    return text if REFERENCE.fullmatch(text) else ""


def short_name(applicant):
    first = (applicant.firstname or "").split()
    last = (applicant.lastname or "").strip()
    return " ".join(filter(None, [first[0].upper() if first else "", f"{last[0].upper()}." if last else ""]))


def _take_lookup_slot():
    """Shared per-minute ceiling (behind Nginx every visitor has the same address)."""
    limit = getattr(settings, "STATUS_LOOKUP_MAX_PER_MINUTE", 60)
    if limit <= 0:
        return True
    key = f"status-lookup:{timezone.now():%Y%m%d%H%M}"
    cache.add(key, 0, timeout=70)
    try:
        return cache.incr(key) <= limit
    except ValueError:
        return True


def registration_status(applicant):
    """Main registration line, verification line and a short note for the applicant."""
    from core.scheduling import format_window, visit_overdue, visit_window

    rows, note = [], ""
    if applicant.status == "DISAPPROVED":
        rows.append(("New Registration", "Disapproved - please visit the office", "disapproved"))
        return rows, "Please visit the Pio Duran Registration Office for details."
    if not applicant.is_active:
        rows.append(("Registration", "On hold", "disapproved"))
        return rows, "Please visit the Pio Duran Registration Office."
    label, tone = REQUEST_STATUS.get(applicant.status, (applicant.get_status_display(), "pending"))
    rows.append(("New Registration", label, tone))
    if applicant.status != "APPROVED":
        if applicant.possible_duplicate_of_id:
            rows[-1] = ("New Registration", "Pending - possible duplicate", "pending")
            return rows, ("Your registration has the same name and birthdate as an existing record. "
                          "The office will review it and send you an SMS.")
        return rows, "The office will review your application. You will receive an SMS once it is approved."
    if applicant.verification_status == "VERIFIED":
        rows.append(("Verification", "Verified - registration complete", "approved"))
        return rows, ""
    rows.append(("Verification", "Biometrics pending", "review"))
    window = visit_window(applicant)
    if window:
        rows.append(("Office visit", f"Any working day, {format_window(*window)}", "info"))
        note = ("Your visit window has passed. You can still visit the office for fingerprints and signature."
                if visit_overdue(applicant) else
                "Bring a valid ID. Your fingerprints and signature will be taken at the office.")
    else:
        note = "Please visit the Pio Duran Registration Office for fingerprints and signature."
    return rows, note


def service_requests(applicant, limit=5):
    items = []
    for relation, label in REQUESTS:
        for record in getattr(applicant, relation).all():
            status_label, tone = REQUEST_STATUS.get(record.status, (record.get_status_display(), "pending"))
            items.append({"label": label, "date": record.requested_at, "status": status_label, "tone": tone})
    items.sort(key=lambda item: item["date"], reverse=True)
    for item in items:
        item["date"] = timezone.localtime(item["date"]).strftime("%b %d, %Y") if item["date"] else ""
    return items[:limit]


def lookup(raw_reference):
    """Result dict for the template / JSON."""
    reference = normalize_reference(raw_reference)
    if not reference:
        return {"found": False, "message": "Enter a valid reference number, for example PD-C023C0859CC74E6AB6EF261F5033C0D4."}
    applicant = Applicant.objects.filter(registration_reference=reference).first()
    if applicant is None:
        return {"found": False, "message": "No application was found for this reference number."}
    rows, note = registration_status(applicant)
    return {
        "found": True,
        "name": short_name(applicant),
        "reference": reference,
        "rows": [{"label": label, "status": status, "tone": tone} for label, status, tone in rows],
        "note": note,
        "requests": service_requests(applicant),
    }


@csrf_exempt  # read-only lookup; pages may be offline copies without a fresh CSRF token
@require_http_methods(["GET", "POST"])
def status_lookup(request):
    if request.method == "GET":
        return render(request, "applicant/status.html")
    if not _take_lookup_slot():
        result, code = {"found": False, "message": "Too many status checks right now. Please try again in a minute."}, 429
    else:
        result, code = lookup(request.POST.get("reference", "")), 200
    if request.headers.get("X-Status-Fragment") == "1":  # Home page script: just the result block
        return render(request, "components/status_result.html", {"status_result": result}, status=code)
    if request.headers.get("Accept", "").startswith("application/json"):
        return JsonResponse(result, status=code)
    # Works without JavaScript: show the page again with the result.
    return render(request, "applicant/status.html",
                  {"status_result": result, "status_reference": request.POST.get("reference", "")}, status=code)
