from Applicants.profile_details import apply_profile_details
from Applicants.application_types import APPLICATION_TYPE_LABELS
from .biometric_state import SIGNATURE_FIELDS, file_exists as biometric_file_exists, signatures_complete, capture_complete, sync_completion
import base64
import binascii
import json
import re
import io
from io import BytesIO

import logging
import requests
from pathlib import Path
from datetime import timedelta, datetime
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from Applicants.models import Barangay
from django.contrib.auth import authenticate, login, logout
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponse
from Applicants.models import (
    Applicant,
    ApplicantBiometric,
    ApplicantNotification,
    ApplicantUpdateRequest,
    ApplicantTransferRequest,
    ApplicantReactivationRequest,
    ApplicantReinstatementRequest,
    SignatureSession,
    FingerprintCaptureRequest
)
from core.fingerprint.scanner import capture_fingerprint
from django.utils import timezone
from django.db.models.deletion import ProtectedError
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.core.files import File
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from PIL import Image, UnidentifiedImageError

logger = logging.getLogger(__name__)


def keep_alive(request):
    return JsonResponse({
        "status": "ok",
        "service": "Django API",
        "timestamp": timezone.now().isoformat(),
    })

def admin_superuser_required(request):

    if not request.user.is_authenticated:
        return redirect("admin-login")

    if not request.user.is_superuser:
        logout(request)
        return redirect("admin-login")

    return None


def admin_login(request):

    if request.user.is_authenticated and request.user.is_superuser:
        return redirect("dashboard")

    if request.method == "POST":

        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        if not username:
            return render(
                request,
                "comelec/auth/login.html",
                {
                    "error": "Username is required."
                }
            )

        if not password:
            return render(
                request,
                "comelec/auth/login.html",
                {
                    "error": "Password is required."
                }
            )

        from .admin_security import authenticate_admin
        user, error = authenticate_admin(request, username, password)
        if error:
            response = render(request, "comelec/auth/login.html", {"error": error})
            if error.startswith("Too many"):
                response.status_code = 429
                response["Retry-After"] = "900"
            return response

        login(request, user)

        return redirect("dashboard")

    return render(
        request,
        "comelec/auth/login.html"
    )

@login_required
def admin_dashboard(request):

    # =========================================================
    # ADMIN AUTHENTICATION
    # =========================================================

    if not request.user.is_authenticated:
        return redirect("admin-login")

    if not request.user.is_superuser:
        logout(request)
        return redirect("admin-login")

    # =========================================================
    # APPLICATION COUNTS
    # =========================================================

    # ---------------------------------------------------------
    # NEW REGISTRATION
    # ---------------------------------------------------------

    new_pending = Applicant.objects.filter(
        status="PENDING"
    ).count()

    new_review = Applicant.objects.filter(
        status="REVIEW"
    ).count()

    new_approved = Applicant.objects.filter(
        status="APPROVED"
    ).count()

    new_disapproved = Applicant.objects.filter(
        status="DISAPPROVED"
    ).count()

    # ---------------------------------------------------------
    # UPDATE INFORMATION
    # ---------------------------------------------------------

    update_pending = ApplicantUpdateRequest.objects.filter(
        status="PENDING"
    ).count()

    update_review = ApplicantUpdateRequest.objects.filter(
        status="REVIEW"
    ).count()

    update_approved = ApplicantUpdateRequest.objects.filter(
        status="APPROVED"
    ).count()

    update_disapproved = ApplicantUpdateRequest.objects.filter(
        status="DISAPPROVED"
    ).count()

    # ---------------------------------------------------------
    # TRANSFER
    # ---------------------------------------------------------

    transfer_pending = ApplicantTransferRequest.objects.filter(
        status="PENDING"
    ).count()

    transfer_review = ApplicantTransferRequest.objects.filter(
        status="REVIEW"
    ).count()

    transfer_approved = ApplicantTransferRequest.objects.filter(
        status="APPROVED"
    ).count()

    transfer_disapproved = ApplicantTransferRequest.objects.filter(
        status="DISAPPROVED"
    ).count()

    # ---------------------------------------------------------
    # REACTIVATION
    # ---------------------------------------------------------

    reactivation_pending = ApplicantReactivationRequest.objects.filter(
        status="PENDING"
    ).count()

    reactivation_review = ApplicantReactivationRequest.objects.filter(
        status="REVIEW"
    ).count()

    reactivation_approved = ApplicantReactivationRequest.objects.filter(
        status="APPROVED"
    ).count()

    reactivation_disapproved = ApplicantReactivationRequest.objects.filter(
        status="DISAPPROVED"
    ).count()

    # ---------------------------------------------------------
    # REINSTATEMENT
    # ---------------------------------------------------------

    reinstatement_pending = ApplicantReinstatementRequest.objects.filter(
        status="PENDING"
    ).count()

    reinstatement_review = ApplicantReinstatementRequest.objects.filter(
        status="REVIEW"
    ).count()

    reinstatement_approved = ApplicantReinstatementRequest.objects.filter(
        status="APPROVED"
    ).count()

    reinstatement_disapproved = ApplicantReinstatementRequest.objects.filter(
        status="DISAPPROVED"
    ).count()

    # =========================================================
    # TOTAL APPLICATION STATUS
    # =========================================================

    pending_total = (
        new_pending
        + update_pending
        + transfer_pending
        + reactivation_pending
        + reinstatement_pending
    )

    review_total = (
        new_review
        + update_review
        + transfer_review
        + reactivation_review
        + reinstatement_review
    )

    approved_total = (
        new_approved
        + update_approved
        + transfer_approved
        + reactivation_approved
        + reinstatement_approved
    )

    disapproved_total = (
        new_disapproved
        + update_disapproved
        + transfer_disapproved
        + reactivation_disapproved
        + reinstatement_disapproved
    )

    total_applications = (
        pending_total
        + review_total
        + approved_total
        + disapproved_total
    )

    # =========================================================
    # APPLICANT STATUS
    # =========================================================

    approved_applicants = Applicant.objects.filter(
        status="APPROVED"
    ).count()

    inactive_applicants = Applicant.objects.filter(
        is_active=False
    ).count()

    # =========================================================
    # BIOMETRICS
    # =========================================================

    biometrics_pending = Applicant.objects.filter(
        status="APPROVED",
        verification_status="BIOMETRICS_PENDING"
    ).count()

    # Fully verified applicants
    # Signature requirement REMOVED
    fully_verified = Applicant.objects.filter(
        status="APPROVED",
        verification_status="VERIFIED",
        is_active=True,
        biometric__biometrics_completed=True,
        biometric__completed=True,
    ).count()

    # =========================================================
    # BARANGAYS
    # =========================================================

    barangay_count = Barangay.objects.count()

    # =========================================================
    # RECENT APPLICATIONS
    # =========================================================

    recent_applicants = Applicant.objects.select_related(
        "brgy"
    ).order_by(
        "-date_joined",
        "-id"
    )[:5]

    # =========================================================
    # APPLICATION TYPE SUMMARY
    # =========================================================

    application_summary = [
        {
            "name": "New Registration",
            "total": Applicant.objects.count(),
            "pending": new_pending,
            "review": new_review,
            "approved": new_approved,
            "disapproved": new_disapproved,
        },
        {
            "name": "Update Information",
            "total": ApplicantUpdateRequest.objects.count(),
            "pending": update_pending,
            "review": update_review,
            "approved": update_approved,
            "disapproved": update_disapproved,
        },
        {
            "name": "Transfer",
            "total": ApplicantTransferRequest.objects.count(),
            "pending": transfer_pending,
            "review": transfer_review,
            "approved": transfer_approved,
            "disapproved": transfer_disapproved,
        },
        {
            "name": "Reactivation",
            "total": ApplicantReactivationRequest.objects.count(),
            "pending": reactivation_pending,
            "review": reactivation_review,
            "approved": reactivation_approved,
            "disapproved": reactivation_disapproved,
        },
        {
            "name": "Reinstatement",
            "total": ApplicantReinstatementRequest.objects.count(),
            "pending": reinstatement_pending,
            "review": reinstatement_review,
            "approved": reinstatement_approved,
            "disapproved": reinstatement_disapproved,
        },
    ]

    # =========================================================
    # RENDER
    # =========================================================

    barangay_distribution = list(
        Barangay.objects.annotate(total=Count("applicant")).order_by("-total", "name").values("name", "total")
    )
    barangay_distribution = [{"brgy__name": item["name"], "total": item["total"]} for item in barangay_distribution]
    unassigned_count = Applicant.objects.filter(brgy__isnull=True).count()
    if unassigned_count:
        barangay_distribution.append({"brgy__name": "Unassigned", "total": unassigned_count})
    dashboard_chart_data = {
        "types": {"labels": [item["name"] for item in application_summary], "values": [item["total"] for item in application_summary]},
        "statuses": {"labels": ["Pending", "In review", "Approved", "Disapproved"], "values": [pending_total, review_total, approved_total, disapproved_total]},
        "barangays": {"labels": [item["brgy__name"] or "Unassigned" for item in barangay_distribution], "values": [item["total"] for item in barangay_distribution]},
    }

    from .registration_analytics import registration_analytics
    dashboard_analytics = registration_analytics(timezone.localdate().year)
    dashboard_chart_data.update(dashboard_analytics["charts"])

    return render(
        request,
        "comelec/dashboard.html",
        {
            # Main statistics
            "pending_total": pending_total,
            "approved_applicants": approved_applicants,
            "inactive_applicants": inactive_applicants,
            "barangay_count": barangay_count,

            # Application status
            "total_applications": total_applications,
            "review_total": review_total,
            "approved_total": approved_total,
            "disapproved_total": disapproved_total,

            # Verification
            "biometrics_pending": biometrics_pending,
            "fully_verified": fully_verified,

            # Recent applications
            "recent_applicants": recent_applicants,

            # Application summary
            "application_summary": application_summary,
            "dashboard_chart_data": dashboard_chart_data,
            "registration_analytics": dashboard_analytics,
        }
    )

def admin_logout(request):

    logout(request)

    return redirect("admin-login")


@login_required
def add_brgy(request):
    from .barangays import PIO_DURAN_BARANGAYS, canonical_barangay_name, normalize_barangay_name

    existing = {normalize_barangay_name(name) for name in Barangay.objects.values_list("name", flat=True)}
    available = [name for name in PIO_DURAN_BARANGAYS if normalize_barangay_name(name) not in existing]
    context = {"available_barangays": available}
    if request.method == "POST":
        submitted = request.POST.get("name", "").strip()
        name = canonical_barangay_name(submitted)
        context["name"] = submitted
        if name is None:
            context["error"] = "Select a barangay from the official Pio Duran list."
        elif normalize_barangay_name(name) in existing:
            context["error"] = "This barangay is already registered."
        else:
            _, created = Barangay.objects.get_or_create(name=name)
            if created:
                return redirect("brgy_list")
            context["error"] = "This barangay is already registered."
    return render(request, "comelec/brgy_form.html", context)

@login_required
def brgy_list(request):

    barangays = Barangay.objects.all().order_by("name")

    for barangay in barangays:
        barangay.verified_applicant_count = Applicant.objects.filter(
            brgy=barangay,
            status="APPROVED",
            verification_status="VERIFIED",
            is_active=True
        ).count()

    return render(
        request,
        "comelec/brgy_list.html",
        {
            "barangays": barangays
        }
    )

@login_required
def barangay_applicants(request, pk):
    access = admin_superuser_required(request)
    if access:
        return access
    barangay = get_object_or_404(Barangay, pk=pk)
    records = Applicant.objects.filter(brgy=barangay, status="APPROVED",
        verification_status="VERIFIED", is_active=True)
    selected = request.GET.get("application_type", "").upper()
    short_labels = [("", "All"), ("NEW", "New Registration"), ("UPDATE", "Correction"),
        ("TRANSFER", "Transfer"), ("REACTIVATION", "Reactivation"), ("REINSTATEMENT", "Reinstatement")]
    if selected not in dict(short_labels):
        selected = ""
    request_models = {"UPDATE": ApplicantUpdateRequest, "TRANSFER": ApplicantTransferRequest,
        "REACTIVATION": ApplicantReactivationRequest, "REINSTATEMENT": ApplicantReinstatementRequest}
    tabs = []
    filtered = records
    for code, label in short_labels:
        subset = records
        if code in request_models:
            approved_ids = request_models[code].objects.filter(status="APPROVED").values("applicant_id")
            subset = records.filter(Q(application_type=code) | Q(pk__in=approved_ids))
        elif code:
            subset = records.filter(application_type=code)
        tabs.append({"code": code, "label": label, "count": subset.count()})
        if code == selected:
            filtered = subset
    return render(request, "comelec/barangay_applicants.html", {
        "barangay": barangay,
        "applicants": filtered.order_by("lastname", "firstname", "middlename", "pk"),
        "application_type_tabs": tabs, "selected_application_type": selected,
        "selected_application_label": APPLICATION_TYPE_LABELS.get(selected, ""),
        "total_verified": records.count(),
    })

@login_required
def delete_brgy(request, pk):
    access_error = admin_superuser_required(request)
    if access_error:
        return access_error
    barangay = get_object_or_404(Barangay, pk=pk)
    error = None
    if request.method == "POST":
        try:
            barangay.delete()
        except ProtectedError:
            error = "This barangay cannot be deleted because it is used by an applicant or registration request."
            if request.headers.get("Accept") == "application/json":
                return JsonResponse({"error": error}, status=409)
        else:
            if request.headers.get("Accept") == "application/json":
                return JsonResponse({"deleted": True})
            return redirect("brgy_list")
    return render(request, "comelec/brgy_delete.html", {
        "barangay": barangay, "delete_error": error,
    }, status=409 if error else 200)

@login_required
def admin_applications(request):

    if not request.user.is_authenticated:
        return redirect("admin-login")

    if not request.user.is_superuser:
        logout(request)
        return redirect("admin-login")

    # =========================================================
    # SEARCH / FILTER VALUES
    # =========================================================

    search = request.GET.get(
        "search",
        ""
    ).strip()

    application_type = request.GET.get(
        "application_type",
        ""
    ).strip()

    status = request.GET.get(
        "status",
        ""
    ).strip()

    date_from = request.GET.get(
        "date_from",
        ""
    ).strip()

    date_to = request.GET.get(
        "date_to",
        ""
    ).strip()

    # =========================================================
    # APPLICATION LIST
    # =========================================================

    applications = []

    # =========================================================
    # NEW REGISTRATIONS
    # =========================================================

    if not application_type or application_type == "NEW":

        applicants = (
            Applicant.objects
            .all()
            .select_related("brgy")
        )

        if search:
            applicants = applicants.filter(
                Q(lastname__icontains=search) |
                Q(firstname__icontains=search) |
                Q(middlename__icontains=search) |
                Q(email__icontains=search) |
                Q(phone__icontains=search)
            )

        if status:
            applicants = applicants.filter(
                status=status
            )

        if date_from:
            applicants = applicants.filter(
                date_joined__gte=date_from
            )

        if date_to:
            applicants = applicants.filter(
                date_joined__lte=date_to
            )

        for applicant in applicants:

            # =================================================
            # Convert DateField to timezone-aware datetime
            # =================================================

            application_date = timezone.make_aware(
                datetime.combine(
                    applicant.date_joined,
                    datetime.min.time()
                )
            )

            applications.append({
                "id": applicant.id,
                "applicant": applicant,
                "applicant_name": str(applicant),
                "type": "NEW",
                "type_display": APPLICATION_TYPE_LABELS["NEW"],
                "status": applicant.status,
                "status_display": applicant.get_status_display(),
                "date": application_date,
                "url_name": "admin-application-new-detail",
            })

    # =========================================================
    # UPDATE / CORRECTION
    # =========================================================

    if not application_type or application_type == "UPDATE":

        update_requests = (
            ApplicantUpdateRequest.objects
            .all()
            .select_related(
                "applicant",
                "brgy"
            )
        )

        if search:
            update_requests = update_requests.filter(
                Q(applicant__lastname__icontains=search) |
                Q(applicant__firstname__icontains=search) |
                Q(applicant__middlename__icontains=search) |
                Q(applicant__email__icontains=search)
            )

        if status:
            update_requests = update_requests.filter(
                status=status
            )

        if date_from:
            update_requests = update_requests.filter(
                requested_at__date__gte=date_from
            )

        if date_to:
            update_requests = update_requests.filter(
                requested_at__date__lte=date_to
            )

        for application in update_requests:

            applications.append({
                "id": application.id,
                "applicant": application.applicant,
                "applicant_name": str(application.applicant),
                "type": "UPDATE",
                "type_display": APPLICATION_TYPE_LABELS["UPDATE"],
                "status": application.status,
                "status_display": application.get_status_display(),
                "date": application.requested_at,
                "url_name": "admin-application-update-detail",
            })

    # =========================================================
    # TRANSFER
    # =========================================================

    if not application_type or application_type == "TRANSFER":

        transfer_requests = (
            ApplicantTransferRequest.objects
            .all()
            .select_related(
                "applicant",
                "current_brgy",
                "new_brgy"
            )
        )

        if search:
            transfer_requests = transfer_requests.filter(
                Q(applicant__lastname__icontains=search) |
                Q(applicant__firstname__icontains=search) |
                Q(applicant__middlename__icontains=search) |
                Q(applicant__email__icontains=search)
            )

        if status:
            transfer_requests = transfer_requests.filter(
                status=status
            )

        if date_from:
            transfer_requests = transfer_requests.filter(
                requested_at__date__gte=date_from
            )

        if date_to:
            transfer_requests = transfer_requests.filter(
                requested_at__date__lte=date_to
            )

        for application in transfer_requests:

            applications.append({
                "id": application.id,
                "applicant": application.applicant,
                "applicant_name": str(application.applicant),
                "type": "TRANSFER",
                "type_display": APPLICATION_TYPE_LABELS["TRANSFER"],
                "status": application.status,
                "status_display": application.get_status_display(),
                "date": application.requested_at,
                "url_name": "admin-application-transfer-detail",
            })

    # =========================================================
    # REACTIVATION
    # =========================================================

    if not application_type or application_type == "REACTIVATION":

        reactivation_requests = (
            ApplicantReactivationRequest.objects
            .all()
            .select_related(
                "applicant"
            )
        )

        if search:
            reactivation_requests = reactivation_requests.filter(
                Q(applicant__lastname__icontains=search) |
                Q(applicant__firstname__icontains=search) |
                Q(applicant__middlename__icontains=search) |
                Q(applicant__email__icontains=search)
            )

        if status:
            reactivation_requests = reactivation_requests.filter(
                status=status
            )

        if date_from:
            reactivation_requests = reactivation_requests.filter(
                requested_at__date__gte=date_from
            )

        if date_to:
            reactivation_requests = reactivation_requests.filter(
                requested_at__date__lte=date_to
            )

        for application in reactivation_requests:

            applications.append({
                "id": application.id,
                "applicant": application.applicant,
                "applicant_name": str(application.applicant),
                "type": "REACTIVATION",
                "type_display": APPLICATION_TYPE_LABELS["REACTIVATION"],
                "status": application.status,
                "status_display": application.get_status_display(),
                "date": application.requested_at,
                "url_name": "admin-application-reactivation-detail",
            })

    # =========================================================
    # REINSTATEMENT
    # =========================================================

    if not application_type or application_type == "REINSTATEMENT":

        reinstatement_requests = (
            ApplicantReinstatementRequest.objects
            .all()
            .select_related(
                "applicant"
            )
        )

        if search:
            reinstatement_requests = reinstatement_requests.filter(
                Q(applicant__lastname__icontains=search) |
                Q(applicant__firstname__icontains=search) |
                Q(applicant__middlename__icontains=search) |
                Q(applicant__email__icontains=search)
            )

        if status:
            reinstatement_requests = reinstatement_requests.filter(
                status=status
            )

        if date_from:
            reinstatement_requests = reinstatement_requests.filter(
                requested_at__date__gte=date_from
            )

        if date_to:
            reinstatement_requests = reinstatement_requests.filter(
                requested_at__date__lte=date_to
            )

        for application in reinstatement_requests:

            applications.append({
                "id": application.id,
                "applicant": application.applicant,
                "applicant_name": str(application.applicant),
                "type": "REINSTATEMENT",
                "type_display": APPLICATION_TYPE_LABELS["REINSTATEMENT"],
                "status": application.status,
                "status_display": application.get_status_display(),
                "date": application.requested_at,
                "url_name": "admin-application-reinstatement-detail",
            })

    # =========================================================
    # SORT
    # =========================================================

    applications.sort(
        key=lambda item: item["date"],
        reverse=True
    )

    # =========================================================
    # PAGINATION
    # =========================================================

    paginator = Paginator(
        applications,
        10
    )

    page_number = request.GET.get(
        "page"
    )

    page_obj = paginator.get_page(
        page_number
    )

    # =========================================================
    # CONTEXT
    # =========================================================

    context = {
        "page_obj": page_obj,
        "search": search,
        "application_type": application_type,
        "status": status,
        "date_from": date_from,
        "date_to": date_to,
    }

    return render(
        request,
        "comelec/applications/list.html",
        context
    )


# =========================================================
# NEW REGISTRATION DETAIL
# =========================================================
@login_required
def admin_application_new_detail(request, application_id):

    access = admin_superuser_required(request)

    if access:
        return access

    application = get_object_or_404(
        Applicant,
        id=application_id
    )

    return render(
        request,
        "comelec/applications/new_detail.html",
        {
            "application": application,
        }
    )


# =========================================================
# UPDATE / CORRECTION DETAIL
# =========================================================
@login_required
def admin_application_update_detail(request, application_id):

    access = admin_superuser_required(request)

    if access:
        return access

    application = get_object_or_404(
        ApplicantUpdateRequest.objects.select_related(
            "applicant",
            "brgy"
        ),
        id=application_id
    )

    return render(
        request,
        "comelec/applications/update_detail.html",
        {
            "application": application,
        }
    )


# =========================================================
# TRANSFER DETAIL
# =========================================================
@login_required
def admin_application_transfer_detail(request, application_id):

    access = admin_superuser_required(request)

    if access:
        return access

    application = get_object_or_404(
        ApplicantTransferRequest.objects.select_related(
            "applicant",
            "current_brgy",
            "new_brgy"
        ),
        id=application_id
    )

    return render(
        request,
        "comelec/applications/transfer_detail.html",
        {
            "application": application,
        }
    )


# =========================================================
# REACTIVATION DETAIL
# =========================================================
@login_required
def admin_application_reactivation_detail(request, application_id):

    access = admin_superuser_required(request)

    if access:
        return access

    application = get_object_or_404(
        ApplicantReactivationRequest.objects.select_related(
            "applicant"
        ),
        id=application_id
    )

    return render(
        request,
        "comelec/applications/reactivation_detail.html",
        {
            "application": application,
        }
    )


# =========================================================
# REINSTATEMENT DETAIL
# =========================================================
@login_required
def admin_application_reinstatement_detail(request, application_id):

    access = admin_superuser_required(request)

    if access:
        return access

    application = get_object_or_404(
        ApplicantReinstatementRequest.objects.select_related(
            "applicant"
        ),
        id=application_id
    )

    return render(
        request,
        "comelec/applications/reinstatement_detail.html",
        {
            "application": application,
        }
    )

def approve_applicant_for_biometrics(applicant, notification_title, notification_message):

    applicant.status = "APPROVED"
    applicant.is_active = True
    applicant.verification_status = "BIOMETRICS_PENDING"

    applicant.save()

    ApplicantBiometric.objects.get_or_create(
        applicant=applicant
    )

    ApplicantNotification.objects.create(
        applicant=applicant,
        notification_type="BIOMETRICS",
        title=notification_title,
        message=notification_message
    )

def send_iprog_sms(number, message):
    """Queue one SMS with iProg; acceptance does not confirm handset delivery."""
    token = getattr(settings, "IPROG_SMS_API_TOKEN", "").strip()
    if not token:
        logger.error("iProg SMS is not configured: missing IPROG_SMS_API_TOKEN.")
        return False
    number = str(number or "").strip()
    if number.startswith("+63"):
        number = number[1:]
    elif number.startswith("09"):
        number = "63" + number[1:]
    elif number.startswith("9"):
        number = "63" + number
    if not re.fullmatch(r"639[0-9]{9}", number):
        logger.error("iProg SMS: invalid Philippine mobile number.")
        return False
    if not isinstance(message, str) or not message.strip():
        logger.error("iProg SMS: message is empty.")
        return False
    try:
        response = requests.post(
            "https://www.iprogsms.com/api/v1/sms_messages",
            json={"api_token": token, "phone_number": number, "message": message},
            timeout=15,
        )
        if not 200 <= response.status_code < 300:
            logger.error("iProg SMS HTTP failure: %s", response.status_code)
            return False
        result = response.json()
        if not isinstance(result, dict) or str(result.get("status")) != "200" or not result.get("message_id"):
            logger.error("iProg SMS was not accepted.")
            return False
        return True
    except (requests.RequestException, ValueError):
        # Never log credentials, raw responses, recipient details, or retry sends.
        logger.error("iProg SMS request failed or returned invalid JSON.")
        return False


def send_semaphore_sms(number, message):
    """Queue one SMS. True means accepted by Semaphore, not handset delivery."""
    api_key = getattr(settings, "SEMAPHORE_API_KEY", "").strip()
    if not api_key:
        logger.error("Semaphore SMS is not configured: missing SEMAPHORE_API_KEY.")
        return False
    number = str(number or "").strip()
    if number.startswith("+63"):
        number = number[1:]
    elif number.startswith("09"):
        number = "63" + number[1:]
    elif number.startswith("9"):
        number = "63" + number
    if not re.fullmatch(r"639[0-9]{9}", number):
        logger.error("Semaphore SMS: invalid Philippine mobile number.")
        return False
    if not isinstance(message, str) or not message.strip():
        logger.error("Semaphore SMS: message is empty.")
        return False
    payload = {"apikey": api_key, "number": number, "message": message}
    sender_name = getattr(settings, "SEMAPHORE_SENDER_NAME", "").strip()
    if sender_name:
        payload["sendername"] = sender_name
    try:
        response = requests.post(
            "https://api.semaphore.co/api/v4/messages",
            data=payload,
            timeout=15,
        )
        if not 200 <= response.status_code < 300:
            logger.error("Semaphore SMS HTTP failure: %s", response.status_code)
            return False
        result = response.json()
        if not isinstance(result, list) or len(result) != 1:
            logger.error("Semaphore SMS returned an unexpected response.")
            return False
        entry = result[0]
        if (not isinstance(entry, dict) or not entry.get("message_id")
                or str(entry.get("status", "")).lower() not in {"queued", "pending", "sent"}):
            logger.error("Semaphore SMS was not accepted.")
            return False
        logger.info("Semaphore SMS accepted. Message ID: %s", entry["message_id"])
        return True
    except (requests.RequestException, ValueError):
        # Do not log response bodies or request data containing credentials or PII.
        logger.error("Semaphore SMS request failed or returned invalid JSON.")
        return False


OFFICE_DAILY_CAPACITY = 50
DISAPPROVED_STATUS = 7

def assign_office_appointment(applicant):

    today = timezone.localdate()

    appointment_date = today

    while True:

        # =====================================================
        # SKIP SATURDAY
        # =====================================================

        if appointment_date.weekday() == 5:

            appointment_date += timedelta(days=1)

            continue

        # =====================================================
        # SKIP SUNDAY
        # =====================================================

        if appointment_date.weekday() == 6:

            appointment_date += timedelta(days=1)

            continue

        # =====================================================
        # COUNT APPLICANTS ALREADY SCHEDULED
        # =====================================================

        scheduled_count = Applicant.objects.filter(
            office_visit_date=appointment_date
        ).count()

        # =====================================================
        # CHECK DAILY CAPACITY
        # =====================================================

        if scheduled_count < OFFICE_DAILY_CAPACITY:

            appointment_slot = (
                scheduled_count + 1
            )

            applicant.office_visit_date = (
                appointment_date
            )

            applicant.office_visit_slot = (
                appointment_slot
            )

            applicant.save(
                update_fields=[
                    "office_visit_date",
                    "office_visit_slot",
                ]
            )

            return (
                appointment_date,
                appointment_slot
            )

        # =====================================================
        # DAY IS FULL
        # MOVE TO NEXT DAY
        # =====================================================

        appointment_date += timedelta(days=1)


def get_applicant_full_name(applicant):

    return (
        f"{applicant.firstname} "
        f"{applicant.middlename} "
        f"{applicant.lastname}"
    ).strip()


def send_approval_sms(
    applicant,
    application_name
):

    applicant_name = get_applicant_full_name(
        applicant
    )

    appointment_date = (
        applicant.office_visit_date
    )

    appointment_slot = (
        applicant.office_visit_slot
    )

    if appointment_date:

        formatted_date = appointment_date.strftime(
            "%B %d, %Y"
        )

    else:

        formatted_date = "To be announced"

    if appointment_slot:

        appointment_number = (
            f"{appointment_slot} / "
            f"{OFFICE_DAILY_CAPACITY}"
        )

    else:

        appointment_number = "To be announced"

    message = (
        "Voter Registration Services: "
        f"{applicant_name}, your {application_name} "
        "application has been APPROVED. "
        f"Your office appointment is {formatted_date}. "
        f"Appointment No. {appointment_number}. "
        "Please visit the Pio Duran Registration Office "
        "to complete your fingerprint biometrics and "
        "electronic signature. "
        "Your registration is NOT YET VERIFIED until "
        "all biometric requirements are completed."
    )

    return send_iprog_sms(
        applicant.phone,
        message
    )


@login_required
def admin_application_action(
    request,
    application_type,
    application_id,
    action
):

    # =========================================================
    # ADMIN ACCESS
    # =========================================================

    access = admin_superuser_required(request)

    if access:
        return access

    # =========================================================
    # POST ONLY
    # =========================================================

    if request.method != "POST":

        return redirect(
            "admin-applications"
        )

    # =========================================================
    # VALID ACTION
    # =========================================================

    if action not in [
        "review",
        "approve",
        "disapprove",
    ]:

        return redirect(
            "admin-applications"
        )

    # =========================================================
    # DATABASE TRANSACTION
    # =========================================================

    with transaction.atomic():

        # =====================================================
        # NEW REGISTRATION
        # =====================================================

        if application_type == "new":

            application = get_object_or_404(
                Applicant,
                id=application_id
            )

            # -------------------------------------------------
            # REVIEW
            # -------------------------------------------------

            if action == "review":

                application.status = "REVIEW"

                application.save(
                    update_fields=[
                        "status"
                    ]
                )

                return redirect(
                    "admin-application-new-detail",
                    application_id=application.id
                )

            # -------------------------------------------------
            # APPROVE
            # -------------------------------------------------

            elif action == "approve":

                # =============================================
                # APPROVE FOR BIOMETRICS
                # =============================================

                approve_applicant_for_biometrics(
                    applicant=application,
                    notification_title="Registration Approved",
                    notification_message=(
                        "Your voter registration application "
                        "has been approved. Please visit the "
                        "applicant site to complete your "
                        "fingerprint biometrics and electronic "
                        "signature. Your registration will remain "
                        "unverified until all biometric "
                        "requirements are completed."
                    )
                )

                # =============================================
                # ASSIGN OFFICE APPOINTMENT
                # =============================================

                assign_office_appointment(
                    application
                )

                # =============================================
                # iProg SMS
                # =============================================

                send_approval_sms(
                    applicant=application,
                    application_name="New Registration"
                )

                return redirect(
                    "admin-applicant-biometric",
                    applicant_id=application.id
                )

            # -------------------------------------------------
            # DISAPPROVE
            # -------------------------------------------------

            elif action == "disapprove":

                application.status = "DISAPPROVED"
                application.is_active = False

                application.save(
                    update_fields=[
                        "status",
                        "is_active"
                    ]
                )

                # =============================================
                # APPLICANT NAME
                # =============================================

                applicant_name = (
                    get_applicant_full_name(
                        application
                    )
                )

                # =============================================
                # iProg SMS
                # =============================================

                send_iprog_sms(
                    application.phone,
                    (
                        "Voter Registration Services: "
                        f"{applicant_name}, your voter "
                        "registration application has been "
                        "DISAPPROVED. The application may "
                        "contain incorrect or incomplete "
                        "information or may duplicate an "
                        "existing registration or application. "
                        "Please visit the Pio Duran Registration "
                        "Office for clarification."
                    )
                )

                return redirect(
                    "admin-application-new-detail",
                    application_id=application.id
                )

        # =====================================================
        # UPDATE REQUEST
        # =====================================================

        elif application_type == "update":

            application = get_object_or_404(
                ApplicantUpdateRequest.objects.select_related(
                    "applicant",
                    "brgy"
                ),
                id=application_id
            )

            applicant = application.applicant

            # -------------------------------------------------
            # REVIEW
            # -------------------------------------------------

            if action == "review":

                application.status = "REVIEW"
                application.reviewed_at = timezone.now()

                application.save(
                    update_fields=[
                        "status",
                        "reviewed_at"
                    ]
                )

                return redirect(
                    "admin-application-update-detail",
                    application_id=application.id
                )

            # -------------------------------------------------
            # APPROVE
            # -------------------------------------------------

            elif action == "approve":

                # =============================================
                # COPY REQUEST DATA TO APPLICANT
                # =============================================

                applicant.lastname = (
                    application.lastname
                )

                applicant.firstname = (
                    application.firstname
                )

                applicant.middlename = (
                    application.middlename
                )

                applicant.age = (
                    application.age
                )

                applicant.sex = (
                    application.sex
                )

                applicant.birthdate = (
                    application.birthdate
                )

                applicant.birthplace = (
                    application.birthplace
                )

                applicant.brgy = (
                    application.brgy
                )

                applicant.province = (
                    application.province
                )

                applicant.municipality = (
                    application.municipality
                )

                applicant.phone = (
                    application.phone
                )

                applicant.email = (
                    application.email or None
                )

                if application.civil_status:
                    applicant.civil_status = application.civil_status

                applicant.pwd_status = (
                    application.pwd_status
                )

                applicant.citizenship_status = (
                    application.citizenship_status
                )

                applicant.father = (
                    application.father
                )

                applicant.mother = (
                    application.mother
                )

                applicant.is_senior = (
                    application.age >= 60
                )

                # =============================================
                # APPROVE FOR BIOMETRICS
                # =============================================

                apply_profile_details(application, applicant)
                approve_applicant_for_biometrics(
                    applicant=applicant,
                    notification_title="Registration Update Approved",
                    notification_message=(
                        "Your registration update request "
                        "has been approved. Please visit the "
                        "applicant site to complete your "
                        "fingerprint biometrics and electronic "
                        "signature. Your registration will "
                        "remain unverified until all biometric "
                        "requirements are completed."
                    )
                )

                # =============================================
                # REQUEST STATUS
                # =============================================

                application.status = "APPROVED"
                application.reviewed_at = timezone.now()

                application.save(
                    update_fields=[
                        "status",
                        "reviewed_at"
                    ]
                )

                # =============================================
                # ASSIGN OFFICE APPOINTMENT
                # =============================================

                assign_office_appointment(
                    applicant
                )

                # =============================================
                # iProg SMS
                # =============================================

                send_approval_sms(
                    applicant=applicant,
                    application_name="Registration Update"
                )

                return redirect(
                    "admin-applicant-biometric",
                    applicant_id=applicant.id
                )

            # -------------------------------------------------
            # DISAPPROVE
            # -------------------------------------------------

            elif action == "disapprove":

                application.status = "DISAPPROVED"
                application.reviewed_at = timezone.now()

                application.save(
                    update_fields=[
                        "status",
                        "reviewed_at"
                    ]
                )

                applicant_name = (
                    get_applicant_full_name(
                        applicant
                    )
                )

                # =============================================
                # iProg SMS
                # =============================================

                send_iprog_sms(
                    applicant.phone,
                    (
                        "Voter Registration Services: "
                        f"{applicant_name}, your registration "
                        "UPDATE request has been DISAPPROVED. "
                        "The request may contain incorrect or "
                        "incomplete information or may duplicate "
                        "an existing registration or application. "
                        "Please visit the Pio Duran Registration "
                        "Office for clarification."
                    )
                )

                return redirect(
                    "admin-application-update-detail",
                    application_id=application.id
                )

        # =====================================================
        # TRANSFER REQUEST
        # =====================================================

        elif application_type == "transfer":

            application = get_object_or_404(
                ApplicantTransferRequest.objects.select_related(
                    "applicant",
                    "current_brgy",
                    "new_brgy"
                ),
                id=application_id
            )

            applicant = application.applicant

            # -------------------------------------------------
            # REVIEW
            # -------------------------------------------------

            if action == "review":

                application.status = "REVIEW"
                application.reviewed_at = timezone.now()

                application.save(
                    update_fields=[
                        "status",
                        "reviewed_at"
                    ]
                )

                return redirect(
                    "admin-application-transfer-detail",
                    application_id=application.id
                )

            # -------------------------------------------------
            # APPROVE
            # -------------------------------------------------

            elif action == "approve":

                # =============================================
                # UPDATE ADDRESS
                # =============================================

                applicant.brgy = (
                    application.new_brgy
                )

                applicant.municipality = (
                    application.new_municipality
                )

                applicant.province = (
                    application.new_province
                )

                # =============================================
                # APPROVE FOR BIOMETRICS
                # =============================================

                apply_profile_details(application, applicant)
                approve_applicant_for_biometrics(
                    applicant=applicant,
                    notification_title="Transfer Request Approved",
                    notification_message=(
                        "Your voter registration transfer "
                        "request has been approved. Please "
                        "visit the applicant site to complete "
                        "your fingerprint biometrics and "
                        "electronic signature. Your registration "
                        "will remain unverified until all "
                        "biometric requirements are completed."
                    )
                )

                # =============================================
                # REQUEST STATUS
                # =============================================

                application.status = "APPROVED"
                application.reviewed_at = timezone.now()

                application.save(
                    update_fields=[
                        "status",
                        "reviewed_at"
                    ]
                )

                # =============================================
                # ASSIGN OFFICE APPOINTMENT
                # =============================================

                assign_office_appointment(
                    applicant
                )

                # =============================================
                # iProg SMS
                # =============================================

                send_approval_sms(
                    applicant=applicant,
                    application_name="Transfer"
                )

                return redirect(
                    "admin-applicant-biometric",
                    applicant_id=applicant.id
                )

            # -------------------------------------------------
            # DISAPPROVE
            # -------------------------------------------------

            elif action == "disapprove":

                application.status = "DISAPPROVED"
                application.reviewed_at = timezone.now()

                application.save(
                    update_fields=[
                        "status",
                        "reviewed_at"
                    ]
                )

                applicant_name = (
                    get_applicant_full_name(
                        applicant
                    )
                )

                # =============================================
                # iProg SMS
                # =============================================

                send_iprog_sms(
                    applicant.phone,
                    (
                        "Voter Registration Services: "
                        f"{applicant_name}, your TRANSFER "
                        "request has been DISAPPROVED. The "
                        "request may contain incorrect or "
                        "incomplete information or may duplicate "
                        "an existing registration or application. "
                        "Please visit the Pio Duran Registration "
                        "Office for clarification."
                    )
                )

                return redirect(
                    "admin-application-transfer-detail",
                    application_id=application.id
                )

        # =====================================================
        # REACTIVATION REQUEST
        # =====================================================

        elif application_type == "reactivation":

            application = get_object_or_404(
                ApplicantReactivationRequest.objects.select_related(
                    "applicant"
                ),
                id=application_id
            )

            applicant = application.applicant

            # -------------------------------------------------
            # REVIEW
            # -------------------------------------------------

            if action == "review":

                application.status = "REVIEW"
                application.reviewed_at = timezone.now()

                application.save(
                    update_fields=[
                        "status",
                        "reviewed_at"
                    ]
                )

                return redirect(
                    "admin-application-reactivation-detail",
                    application_id=application.id
                )

            # -------------------------------------------------
            # APPROVE
            # -------------------------------------------------

            elif action == "approve":

                # =============================================
                # APPROVE FOR BIOMETRICS
                # =============================================

                apply_profile_details(application, applicant)
                approve_applicant_for_biometrics(
                    applicant=applicant,
                    notification_title="Reactivation Approved",
                    notification_message=(
                        "Your voter registration reactivation "
                        "request has been approved. Please visit "
                        "the applicant site to complete your "
                        "fingerprint biometrics and electronic "
                        "signature. Your registration will remain "
                        "unverified until all biometric "
                        "requirements are completed."
                    )
                )

                # =============================================
                # REQUEST STATUS
                # =============================================

                application.status = "APPROVED"
                application.reviewed_at = timezone.now()

                application.save(
                    update_fields=[
                        "status",
                        "reviewed_at"
                    ]
                )

                # =============================================
                # ASSIGN OFFICE APPOINTMENT
                # =============================================

                assign_office_appointment(
                    applicant
                )

                # =============================================
                # iProg SMS
                # =============================================

                send_approval_sms(
                    applicant=applicant,
                    application_name="Reactivation"
                )

                return redirect(
                    "admin-applicant-biometric",
                    applicant_id=applicant.id
                )

            # -------------------------------------------------
            # DISAPPROVE
            # -------------------------------------------------

            elif action == "disapprove":

                application.status = "DISAPPROVED"
                application.reviewed_at = timezone.now()

                application.save(
                    update_fields=[
                        "status",
                        "reviewed_at"
                    ]
                )

                applicant_name = (
                    get_applicant_full_name(
                        applicant
                    )
                )

                # =============================================
                # iProg SMS
                # =============================================

                send_iprog_sms(
                    applicant.phone,
                    (
                        "Voter Registration Services: "
                        f"{applicant_name}, your REACTIVATION "
                        "request has been DISAPPROVED. The "
                        "request may contain incorrect or "
                        "incomplete information or may duplicate "
                        "an existing registration or application. "
                        "Please visit the Pio Duran Registration "
                        "Office for clarification."
                    )
                )

                return redirect(
                    "admin-application-reactivation-detail",
                    application_id=application.id
                )

        # =====================================================
        # REINSTATEMENT REQUEST
        # =====================================================

        elif application_type == "reinstatement":

            application = get_object_or_404(
                ApplicantReinstatementRequest.objects.select_related(
                    "applicant"
                ),
                id=application_id
            )

            applicant = application.applicant

            # -------------------------------------------------
            # REVIEW
            # -------------------------------------------------

            if action == "review":

                application.status = "REVIEW"
                application.reviewed_at = timezone.now()

                application.save(
                    update_fields=[
                        "status",
                        "reviewed_at"
                    ]
                )

                return redirect(
                    "admin-application-reinstatement-detail",
                    application_id=application.id
                )

            # -------------------------------------------------
            # APPROVE
            # -------------------------------------------------

            elif action == "approve":

                # =============================================
                # APPROVE FOR BIOMETRICS
                # =============================================

                apply_profile_details(application, applicant)
                approve_applicant_for_biometrics(
                    applicant=applicant,
                    notification_title="Reinstatement Approved",
                    notification_message=(
                        "Your voter registration reinstatement "
                        "request has been approved. Please visit "
                        "the applicant site to complete your "
                        "fingerprint biometrics and electronic "
                        "signature. Your registration will remain "
                        "unverified until all biometric "
                        "requirements are completed."
                    )
                )

                # =============================================
                # REQUEST STATUS
                # =============================================

                application.status = "APPROVED"
                application.reviewed_at = timezone.now()

                application.save(
                    update_fields=[
                        "status",
                        "reviewed_at"
                    ]
                )

                # =============================================
                # ASSIGN OFFICE APPOINTMENT
                # =============================================

                assign_office_appointment(
                    applicant
                )

                # =============================================
                # iProg SMS
                # =============================================

                send_approval_sms(
                    applicant=applicant,
                    application_name="Reinstatement"
                )

                return redirect(
                    "admin-applicant-biometric",
                    applicant_id=applicant.id
                )

            # -------------------------------------------------
            # DISAPPROVE
            # -------------------------------------------------

            elif action == "disapprove":

                application.status = "DISAPPROVED"
                application.reviewed_at = timezone.now()

                application.save(
                    update_fields=[
                        "status",
                        "reviewed_at"
                    ]
                )

                applicant_name = (
                    get_applicant_full_name(
                        applicant
                    )
                )

                # =============================================
                # iProg SMS
                # =============================================

                send_iprog_sms(
                    applicant.phone,
                    (
                        "Voter Registration Services: "
                        f"{applicant_name}, your REINSTATEMENT "
                        "request has been DISAPPROVED. The "
                        "request may contain incorrect or "
                        "incomplete information or may duplicate "
                        "an existing registration or application. "
                        "Please visit the Pio Duran Registration "
                        "Office for clarification."
                    )
                )

                return redirect(
                    "admin-application-reinstatement-detail",
                    application_id=application.id
                )

    # =========================================================
    # DEFAULT REDIRECT
    # =========================================================

    return redirect(
        "admin-applications"
    )



def admin_applicant_biometric(request, applicant_id):
    access = admin_superuser_required(request)

    if access:
        return access

    applicant = get_object_or_404(
        Applicant,
        id=applicant_id
    )

    biometric, created = ApplicantBiometric.objects.get_or_create(
        applicant=applicant
    )

    # Check the actual files in the configured storage.
    def file_exists(field):
        if not field or not field.name:
            return False

        try:
            return field.storage.exists(field.name)
        except (OSError, ValueError):
            return False

    left_image_exists = file_exists(
        biometric.left_finger
    )

    right_image_exists = file_exists(
        biometric.right_finger
    )

    signature_exists = file_exists(
        biometric.applicant_signature
    )

    # Keep the capture screen accessible for reviewing and retaking each sample.
    return render(
        request,
        "comelec/applications/biometric.html",
        {
            "applicant": applicant,
            "biometric": biometric,
            "left_image_exists": left_image_exists,
            "right_image_exists": right_image_exists,
            "signature_exists": signature_exists,
            "signature_slots": [{"slot": slot, "field": getattr(biometric, field), "captured": biometric_file_exists(getattr(biometric, field))} for slot, field in SIGNATURE_FIELDS.items()],
            "signatures_complete": signatures_complete(biometric),
            "capture_complete": capture_complete(biometric),
        }
    )


from .signatures import start_signature_session, get_waiting_signature_session, complete_signature_session, signature_session_status

@login_required
@require_POST
def cancel_signature_session(
    request,
    session_id
):
    access = admin_superuser_required(request)
    if access:
        return access
    # ---------------------------------------------------------
    # Get session
    # ---------------------------------------------------------

    try:
        session = (
            SignatureSession.objects
            .get(
                session_id=session_id
            )
        )

    except SignatureSession.DoesNotExist:

        return JsonResponse(
            {
                "success": False,
                "message": "Signature session not found."
            },
            status=404
        )

    # ---------------------------------------------------------
    # Only cancel waiting sessions
    # ---------------------------------------------------------

    if (
        session.status !=
        SignatureSession.STATUS_WAITING
    ):
        return JsonResponse({
            "success": True,
            "message": (
                "Signature session is already closed."
            ),
            "session_id": str(
                session.session_id
            ),
            "status": session.status,
        })

    # ---------------------------------------------------------
    # Cancel session
    # ---------------------------------------------------------

    session.status = (
        SignatureSession.STATUS_CANCELLED
    )

    session.cancelled_at = timezone.now()

    session.save(
        update_fields=[
            "status",
            "cancelled_at",
        ]
    )

    # ---------------------------------------------------------
    # Return result
    # ---------------------------------------------------------

    return JsonResponse({
        "success": True,
        "message": (
            "Signature session cancelled successfully."
        ),
        "session_id": str(
            session.session_id
        ),
        "status": session.status,
    })

@require_POST
def admin_capture_fingerprint(request, applicant_id):

    access = admin_superuser_required(request)

    if access:
        return JsonResponse(
            {
                "success": False,
                "message": "Unauthorized."
            },
            status=403
        )

    applicant = get_object_or_404(
        Applicant,
        id=applicant_id
    )

    biometric, created = ApplicantBiometric.objects.get_or_create(
        applicant=applicant
    )

    finger = request.POST.get("finger")

    if finger not in ["left", "right"]:

        return JsonResponse(
            {
                "success": False,
                "message": "Invalid fingerprint side."
            },
            status=400
        )

    try:

        print()
        print("========================================")
        print("FINGERPRINT CAPTURE")
        print("========================================")
        print(
            f"Applicant ID : {applicant.id}"
        )
        print(
            f"Finger       : {finger}"
        )

        # =====================================================
        # CAPTURE
        # =====================================================

        png_path = capture_fingerprint()

        if not png_path:

            return JsonResponse(
                {
                    "success": False,
                    "message": "No fingerprint image was created."
                },
                status=500
            )

        png_path = Path(png_path)

        print(
            f"Scanner PNG  : {png_path}"
        )

        if not png_path.exists():

            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "Fingerprint PNG does not exist: "
                        f"{png_path}"
                    )
                },
                status=500
            )

        # =====================================================
        # SAVE LEFT
        # =====================================================

        if finger == "left":

            if biometric.left_finger:

                biometric.left_finger.delete(
                    save=False
                )

            filename = (
                f"applicant_{applicant.id}_left_finger.png"
            )

            with open(
                png_path,
                "rb"
            ) as image_file:

                biometric.left_finger.save(
                    filename,
                    File(image_file),
                    save=False
                )

            print(
                f"LEFT FILE    : {biometric.left_finger.name}"
            )

            print(
                f"LEFT URL     : {biometric.left_finger.url}"
            )

            print(
                f"LEFT PATH    : {biometric.left_finger.path}"
            )

        # =====================================================
        # SAVE RIGHT
        # =====================================================

        else:

            if biometric.right_finger:

                biometric.right_finger.delete(
                    save=False
                )

            filename = (
                f"applicant_{applicant.id}_right_finger.png"
            )

            with open(
                png_path,
                "rb"
            ) as image_file:

                biometric.right_finger.save(
                    filename,
                    File(image_file),
                    save=False
                )

            print(
                f"RIGHT FILE   : {biometric.right_finger.name}"
            )

            print(
                f"RIGHT URL    : {biometric.right_finger.url}"
            )

            print(
                f"RIGHT PATH   : {biometric.right_finger.path}"
            )

        # =====================================================
        # CHECK BOTH
        # =====================================================

        biometric.biometrics_completed = capture_complete(biometric)

        biometric.captured_at = timezone.now()

        if biometric.biometrics_completed:

            biometric.completed = True

            applicant.verification_status = "VERIFIED"

            applicant.save(
                update_fields=[
                    "verification_status"
                ]
            )

        else:

            biometric.completed = False
            applicant.verification_status = "BIOMETRICS_PENDING"
            applicant.save(update_fields=["verification_status"])

        biometric.save()

        # =====================================================
        # VERIFY PHYSICAL FILE
        # =====================================================

        if finger == "left":

            saved_path = Path(
                biometric.left_finger.path
            )

            image_url = (
                biometric.left_finger.url
            )

        else:

            saved_path = Path(
                biometric.right_finger.path
            )

            image_url = (
                biometric.right_finger.url
            )

        print()
        print("========================================")
        print("SAVED FINGERPRINT")
        print("========================================")
        print(
            f"Physical Path : {saved_path}"
        )
        print(
            f"File Exists   : {saved_path.exists()}"
        )
        print(
            f"File Size     : {saved_path.stat().st_size if saved_path.exists() else 0}"
        )
        print(
            f"Browser URL   : {image_url}"
        )
        print("========================================")
        print()

        # =====================================================
        # DELETE TEMPORARY SCANNER PNG
        # =====================================================

        try:

            png_path.unlink()

        except Exception:

            pass

        # =====================================================
        # RESPONSE
        # =====================================================

        return JsonResponse(
            {
                "success": True,
                "message": (
                    f"{finger.capitalize()} fingerprint "
                    "captured successfully."
                ),
                "finger": finger,
                "image_url": image_url,
                "biometrics_completed": (
                    biometric.biometrics_completed
                ),
                "completed": (
                    biometric.completed
                ),
            }
        )

    except Exception as e:

        import traceback

        traceback.print_exc()

        return JsonResponse(
            {
                "success": False,
                "message": str(e)
            },
            status=500
        )

@login_required
def print_slip_account(request, applicant_id):

    access = admin_superuser_required(request)

    if access:
        return access

    applicant = get_object_or_404(
        Applicant,
        id=applicant_id
    )

    biometric = get_object_or_404(
        ApplicantBiometric,
        applicant=applicant
    )

    # =========================================================
    # SECURITY CHECK
    # ONLY FULLY VERIFIED APPLICANTS CAN PRINT
    # =========================================================

    if (
        applicant.verification_status != "VERIFIED"
        or not biometric.biometrics_completed
        or not biometric.completed
        or not capture_complete(biometric)
    ):
        return redirect(
            "admin-applicant-biometric",
            applicant_id=applicant.id
        )

    from .receipts import acknowledgment_receipt
    return acknowledgment_receipt(request, applicant_id)

@login_required
def admin_applicants(request):

    access = admin_superuser_required(request)

    if access:
        return access

    # =========================================================
    # ONLY FULLY VERIFIED APPLICANTS
    # =========================================================

    applicants = Applicant.objects.filter(
        status="APPROVED",
        verification_status="VERIFIED",
        is_active=True,
        biometric__biometrics_completed=True,
        biometric__completed=True,
    ).select_related(
        "brgy",
        "biometric"
    ).order_by(
        "-date_joined",
        "-id"
    )

    # =========================================================
    # SEARCH
    # =========================================================

    search = request.GET.get("search", "").strip()

    if search:

        applicants = applicants.filter(
            Q(lastname__icontains=search) |
            Q(firstname__icontains=search) |
            Q(middlename__icontains=search) |
            Q(email__icontains=search) |
            Q(phone__icontains=search)
        )

    # =========================================================
    # BARANGAY FILTER
    # =========================================================

    barangay_id = request.GET.get("barangay", "").strip()

    if barangay_id:

        applicants = applicants.filter(
            brgy_id=barangay_id
        )

    history_view = request.GET.get('view') == 'history'
    application_type = request.GET.get("application_type", "").strip().upper() if history_view else ''
    type_choices = [("NEW", "New Registration"), ("UPDATE", "Correction / Update"),
                    ("TRANSFER", "Transfer"), ("REACTIVATION", "Reactivation"),
                    ("REINSTATEMENT", "Reinstatement")]
    if application_type not in dict(type_choices):
        application_type = ""
    if history_view:
        from .application_history import application_history
        from django.core.paginator import Paginator
        rows = []
        for record in applicants.prefetch_related('update_requests', 'transfer_requests', 'reactivation_requests', 'reinstatement_requests'):
            for item in application_history(record):
                if not application_type or item['type'] == application_type:
                    rows.append(dict(item, applicant=record))
        rows.sort(key=lambda item: item['submitted_at'], reverse=True)
        page_obj = Paginator(rows, 10).get_page(request.GET.get('page'))
        return render(request, 'comelec/applicants/list.html', {
            'history_view': True, 'history_rows': page_obj, 'page_obj': page_obj,
            'barangays': Barangay.objects.all().order_by('name'), 'search': search,
            'barangay_id': barangay_id, 'application_type': application_type,
            'application_type_choices': type_choices,
        })

    if request.GET.get("format") == "print":
        from .report_print import render_application_list
        return render_application_list(request, applicants, ApplicantUpdateRequest.objects.none(),
            ApplicantTransferRequest.objects.none(), ApplicantReactivationRequest.objects.none(),
            ApplicantReinstatementRequest.objects.none(), "", "", applicant_only=True)

    # =========================================================
    # PAGINATION
    # =========================================================

    from django.core.paginator import Paginator

    paginator = Paginator(
        applicants,
        10
    )

    page_number = request.GET.get("page")

    page_obj = paginator.get_page(
        page_number
    )

    barangays = Barangay.objects.all().order_by(
        "name"
    )

    return render(
        request,
        "comelec/applicants/list.html",
        {
            "applicants": page_obj,
            "page_obj": page_obj,
            "barangays": barangays,
            "search": search,
            "barangay_id": barangay_id,
            "application_type": application_type,
            "application_type_choices": type_choices,
        }
    )

@login_required
def admin_applicant_detail(request, applicant_id):

    access = admin_superuser_required(request)

    if access:
        return access

    applicant = get_object_or_404(
        Applicant.objects.select_related(
            "brgy",
            "biometric"
        ),
        id=applicant_id
    )

    biometric = applicant.biometric
    from .application_history import application_history
    history = application_history(applicant)

    return render(
        request,
        "comelec/applicants/detail.html",
        {
            "applicant": applicant,
            "biometric": biometric,
            "application_history": history,
        }
    )


@login_required
def admin_suspend_applicant(request, applicant_id):

    access = admin_superuser_required(request)

    if access:
        return access

    if request.method != "POST":
        return redirect(
            "admin-applicants"
        )

    applicant = get_object_or_404(
        Applicant,
        id=applicant_id
    )

    applicant.is_active = False
    applicant.save(
        update_fields=["is_active"]
    )

    return redirect(
        "admin-applicants"
    )


@login_required
def admin_reports(request):

    access = admin_superuser_required(request)

    if access:
        return access

    # =========================================================
    # FILTERS
    # =========================================================

    # Reports show all applications; old filter parameters are ignored.
    date_from = date_to = application_type = barangay_id = ""

    # =========================================================
    # BASE QUERYSETS
    # =========================================================

    applicants = Applicant.objects.select_related(
        "brgy"
    ).all()

    update_requests = ApplicantUpdateRequest.objects.select_related(
        "applicant",
        "brgy"
    ).all()

    transfer_requests = ApplicantTransferRequest.objects.select_related(
        "applicant",
        "current_brgy",
        "new_brgy"
    ).all()

    reactivation_requests = ApplicantReactivationRequest.objects.select_related(
        "applicant"
    ).all()

    reinstatement_requests = ApplicantReinstatementRequest.objects.select_related(
        "applicant"
    ).all()

    # =========================================================
    # DATE FILTER
    # =========================================================

    if date_from:

        applicants = applicants.filter(
            date_joined__gte=date_from
        )

        update_requests = update_requests.filter(
            requested_at__date__gte=date_from
        )

        transfer_requests = transfer_requests.filter(
            requested_at__date__gte=date_from
        )

        reactivation_requests = reactivation_requests.filter(
            requested_at__date__gte=date_from
        )

        reinstatement_requests = reinstatement_requests.filter(
            requested_at__date__gte=date_from
        )

    if date_to:

        applicants = applicants.filter(
            date_joined__lte=date_to
        )

        update_requests = update_requests.filter(
            requested_at__date__lte=date_to
        )

        transfer_requests = transfer_requests.filter(
            requested_at__date__lte=date_to
        )

        reactivation_requests = reactivation_requests.filter(
            requested_at__date__lte=date_to
        )

        reinstatement_requests = reinstatement_requests.filter(
            requested_at__date__lte=date_to
        )

    # =========================================================
    # BARANGAY FILTER
    # =========================================================

    if barangay_id:

        applicants = applicants.filter(
            brgy_id=barangay_id
        )

        update_requests = update_requests.filter(
            brgy_id=barangay_id
        )

        transfer_requests = transfer_requests.filter(
            Q(current_brgy_id=barangay_id) |
            Q(new_brgy_id=barangay_id)
        )

        # Reactivation and reinstatement do not have barangay
        # fields, so they are filtered through the applicant.

        reactivation_requests = reactivation_requests.filter(
            applicant__brgy_id=barangay_id
        )

        reinstatement_requests = reinstatement_requests.filter(
            applicant__brgy_id=barangay_id
        )

    # =========================================================
    # APPLICATION TYPE FILTER
    # =========================================================

    if application_type:

        if application_type == "NEW":

            update_requests = update_requests.none()
            transfer_requests = transfer_requests.none()
            reactivation_requests = reactivation_requests.none()
            reinstatement_requests = reinstatement_requests.none()

        elif application_type == "UPDATE":

            applicants = applicants.none()
            transfer_requests = transfer_requests.none()
            reactivation_requests = reactivation_requests.none()
            reinstatement_requests = reinstatement_requests.none()

        elif application_type == "TRANSFER":

            applicants = applicants.none()
            update_requests = update_requests.none()
            reactivation_requests = reactivation_requests.none()
            reinstatement_requests = reinstatement_requests.none()

        elif application_type == "REACTIVATION":

            applicants = applicants.none()
            update_requests = update_requests.none()
            transfer_requests = transfer_requests.none()
            reinstatement_requests = reinstatement_requests.none()

        elif application_type == "REINSTATEMENT":

            applicants = applicants.none()
            update_requests = update_requests.none()
            transfer_requests = transfer_requests.none()
            reactivation_requests = reactivation_requests.none()

    from urllib.parse import urlencode
    from django.db.models.functions import ExtractYear
    raw_year = request.GET.get("year", "")
    report_year = int(raw_year) if raw_year.isascii() and raw_year.isdigit() and len(raw_year) == 4 and 1900 <= int(raw_year) <= 9999 else None
    available_years = {timezone.localdate().year}
    sources = [(applicants, "date_joined"), (update_requests, "requested_at"),
        (transfer_requests, "requested_at"), (reactivation_requests, "requested_at"),
        (reinstatement_requests, "requested_at")]
    filtered = []
    for queryset, field in sources:
        available_years.update(queryset.order_by().annotate(report_year=ExtractYear(field)).values_list("report_year", flat=True).distinct())
        if report_year:
            queryset = queryset.filter(**{field + "__year": report_year})
        filtered.append(queryset)
    applicants, update_requests, transfer_requests, reactivation_requests, reinstatement_requests = filtered
    if report_year:
        available_years.add(report_year)
    period_label = str(report_year) if report_year else "All years"
    period_query = urlencode({'year': report_year}) if report_year else ""

    if request.GET.get("format") == "pdf" and request.GET.get("table", "applicants") == "applicants":
        from .report_print import application_list_groups
        from .report_pdf import download_applicant_list
        return download_applicant_list(application_list_groups(applicants, update_requests,
            transfer_requests, reactivation_requests, reinstatement_requests), period_label=period_label)

    if request.GET.get("format") == "print" and request.GET.get("table", "applicants") == "applicants":
        from .report_print import render_application_list
        return render_application_list(request, applicants, update_requests,
            transfer_requests, reactivation_requests, reinstatement_requests,
            date_from, date_to, period_label=period_label)

    # =========================================================
    # TOTALS
    # =========================================================

    new_total = applicants.count()

    update_total = update_requests.count()

    transfer_total = transfer_requests.count()

    reactivation_total = reactivation_requests.count()

    reinstatement_total = reinstatement_requests.count()

    total_applications = (
        new_total
        + update_total
        + transfer_total
        + reactivation_total
        + reinstatement_total
    )

    # =========================================================
    # STATUS TOTALS
    # =========================================================

    pending_total = (
        applicants.filter(status="PENDING").count()
        + update_requests.filter(status="PENDING").count()
        + transfer_requests.filter(status="PENDING").count()
        + reactivation_requests.filter(status="PENDING").count()
        + reinstatement_requests.filter(status="PENDING").count()
    )

    review_total = (
        applicants.filter(status="REVIEW").count()
        + update_requests.filter(status="REVIEW").count()
        + transfer_requests.filter(status="REVIEW").count()
        + reactivation_requests.filter(status="REVIEW").count()
        + reinstatement_requests.filter(status="REVIEW").count()
    )

    approved_total = (
        applicants.filter(status="APPROVED").count()
        + update_requests.filter(status="APPROVED").count()
        + transfer_requests.filter(status="APPROVED").count()
        + reactivation_requests.filter(status="APPROVED").count()
        + reinstatement_requests.filter(status="APPROVED").count()
    )

    disapproved_total = (
        applicants.filter(status="DISAPPROVED").count()
        + update_requests.filter(status="DISAPPROVED").count()
        + transfer_requests.filter(status="DISAPPROVED").count()
        + reactivation_requests.filter(status="DISAPPROVED").count()
        + reinstatement_requests.filter(status="DISAPPROVED").count()
    )

    # =========================================================
    # VERIFIED APPLICANTS
    # =========================================================

    verified_total = applicants.filter(
        status="APPROVED",
        verification_status="VERIFIED",
        is_active=True,
        biometric__biometrics_completed=True,
        biometric__completed=True,
    ).count()

    biometrics_pending_total = applicants.filter(
        status="APPROVED",
        verification_status="BIOMETRICS_PENDING"
    ).count()

    suspended_total = applicants.filter(
        is_active=False
    ).count()

    # =========================================================
    # APPLICATION TYPE REPORT
    # =========================================================

    application_type_report = [
        {
            "code": "NEW",
            "name": APPLICATION_TYPE_LABELS["NEW"],
            "total": new_total,
            "pending": applicants.filter(
                status="PENDING"
            ).count(),
            "review": applicants.filter(
                status="REVIEW"
            ).count(),
            "approved": applicants.filter(
                status="APPROVED"
            ).count(),
            "disapproved": applicants.filter(
                status="DISAPPROVED"
            ).count(),
        },
        {
            "code": "UPDATE",
            "name": APPLICATION_TYPE_LABELS["UPDATE"],
            "total": update_total,
            "pending": update_requests.filter(
                status="PENDING"
            ).count(),
            "review": update_requests.filter(
                status="REVIEW"
            ).count(),
            "approved": update_requests.filter(
                status="APPROVED"
            ).count(),
            "disapproved": update_requests.filter(
                status="DISAPPROVED"
            ).count(),
        },
        {
            "code": "TRANSFER",
            "name": APPLICATION_TYPE_LABELS["TRANSFER"],
            "total": transfer_total,
            "pending": transfer_requests.filter(
                status="PENDING"
            ).count(),
            "review": transfer_requests.filter(
                status="REVIEW"
            ).count(),
            "approved": transfer_requests.filter(
                status="APPROVED"
            ).count(),
            "disapproved": transfer_requests.filter(
                status="DISAPPROVED"
            ).count(),
        },
        {
            "code": "REACTIVATION",
            "name": APPLICATION_TYPE_LABELS["REACTIVATION"],
            "total": reactivation_total,
            "pending": reactivation_requests.filter(
                status="PENDING"
            ).count(),
            "review": reactivation_requests.filter(
                status="REVIEW"
            ).count(),
            "approved": reactivation_requests.filter(
                status="APPROVED"
            ).count(),
            "disapproved": reactivation_requests.filter(
                status="DISAPPROVED"
            ).count(),
        },
        {
            "code": "REINSTATEMENT",
            "name": APPLICATION_TYPE_LABELS["REINSTATEMENT"],
            "total": reinstatement_total,
            "pending": reinstatement_requests.filter(
                status="PENDING"
            ).count(),
            "review": reinstatement_requests.filter(
                status="REVIEW"
            ).count(),
            "approved": reinstatement_requests.filter(
                status="APPROVED"
            ).count(),
            "disapproved": reinstatement_requests.filter(
                status="DISAPPROVED"
            ).count(),
        },
    ]

    # =========================================================
    # BARANGAY REPORT
    # =========================================================

    barangays = Barangay.objects.all().order_by(
        "name"
    )

    barangay_report = []

    for barangay in barangays:

        new_count = applicants.filter(
            brgy=barangay
        ).count()

        update_count = update_requests.filter(
            brgy=barangay
        ).count()

        transfer_count = transfer_requests.filter(
            Q(current_brgy=barangay) |
            Q(new_brgy=barangay)
        ).count()

        reactivation_count = reactivation_requests.filter(
            applicant__brgy=barangay
        ).count()

        reinstatement_count = reinstatement_requests.filter(
            applicant__brgy=barangay
        ).count()

        total = (
            new_count
            + update_count
            + transfer_count
            + reactivation_count
            + reinstatement_count
        )

        verified = applicants.filter(
            brgy=barangay,
            status="APPROVED",
            verification_status="VERIFIED",
            is_active=True,
            biometric__biometrics_completed=True,
            biometric__completed=True,
        ).count()

        barangay_report.append({
            "id": barangay.id,
            "name": barangay.name,
            "new": new_count,
            "update": update_count,
            "transfer": transfer_count,
            "reactivation": reactivation_count,
            "reinstatement": reinstatement_count,
            "total": total,
            "verified": verified,
        })

    # =========================================================
    # CHART DATA
    # =========================================================

    application_chart_labels = [
        item["name"]
        for item in application_type_report
    ]

    application_chart_data = [
        item["total"]
        for item in application_type_report
    ]

    barangay_chart_labels = [
        item["name"]
        for item in barangay_report
        if item["total"] > 0
    ]

    barangay_chart_data = [
        item["total"]
        for item in barangay_report
        if item["total"] > 0
    ]

    status_chart_labels = [
        "Pending",
        "Review",
        "Approved",
        "Disapproved",
    ]

    status_chart_data = [
        pending_total,
        review_total,
        approved_total,
        disapproved_total,
    ]

    # =========================================================
    # RENDER
    # =========================================================

    from .registration_analytics import registration_analytics, TREND_COLUMNS, DEMOGRAPHIC_COLUMNS
    report_analytics = registration_analytics(report_year)

    if request.GET.get("format") in {"pdf", "print"} and request.GET.get("table") in {"types", "barangays", "trends", "demographics"}:
        if request.GET["table"] == "types":
            title, records = "Application Type Report", application_type_report
            columns = [("name", "Application Type"), ("total", "Total"), ("pending", "Pending"),
                ("review", "Review"), ("approved", "Approved"), ("disapproved", "Disapproved")]
        elif request.GET["table"] == "barangays":
            title, records = "Barangay Report", barangay_report
            columns = [("name", "Barangay"), ("new", "New"), ("update", "Update"), ("transfer", "Transfer"),
                ("reactivation", "Reactivation"), ("reinstatement", "Reinstatement"), ("total", "Total"), ("verified", "Verified")]
        elif request.GET["table"] == "trends":
            title, records, columns = "Registration Trends", report_analytics["trends"], TREND_COLUMNS
        else:
            title, records, columns = "Applicant Demographics", report_analytics["demographics"], DEMOGRAPHIC_COLUMNS
        summary_note = ("Unique applicants registered in the selected period. Age as of " + str(report_analytics["as_of"]) if request.GET["table"] == "demographics" else "Application submissions by month or year; change is the count difference from the previous period." if request.GET["table"] == "trends" else "")
        if request.GET["format"] == "pdf":
            from .report_pdf import download_summary
            return download_summary(title, records, columns, period_label, note=summary_note)
        rows = [[record.get(key, "") for key, label in columns] for record in records]
        pages = [rows[offset:offset + 18] for offset in range(0, len(rows), 18)] or [[]]
        return render(request, "comelec/reports_summary_print.html", {"report_title": title,
            "columns": [label for key, label in columns], "pages": pages,
            "period_label": period_label, "summary_note": summary_note, "generated_at": timezone.localtime()})

    from .report_print import application_list_groups
    applicant_list_groups = application_list_groups(applicants, update_requests,
        transfer_requests, reactivation_requests, reinstatement_requests)

    return render(
        request,
        "comelec/reports.html",
        {
            "date_from": date_from,
            "date_to": date_to,
            "application_type": application_type,
            "barangay_id": barangay_id,

            "report_year_options": sorted((year for year in available_years if year), reverse=True),
            "selected_report_year": report_year, "period_label": period_label, "period_query": period_query,
            "registration_analytics": report_analytics,
            "applicant_list_groups": applicant_list_groups,
            "total_applications": total_applications,

            "new_total": new_total,
            "update_total": update_total,
            "transfer_total": transfer_total,
            "reactivation_total": reactivation_total,
            "reinstatement_total": reinstatement_total,

            "pending_total": pending_total,
            "review_total": review_total,
            "approved_total": approved_total,
            "disapproved_total": disapproved_total,

            "verified_total": verified_total,
            "biometrics_pending_total": biometrics_pending_total,
            "suspended_total": suspended_total,

            "application_type_report": application_type_report,
            "barangay_report": barangay_report,
            "barangays": barangays,

            "application_chart_labels": application_chart_labels,
            "application_chart_data": application_chart_data,

            "barangay_chart_labels": barangay_chart_labels,
            "barangay_chart_data": barangay_chart_data,

            "status_chart_labels": status_chart_labels,
            "status_chart_data": status_chart_data,
        }
    )


@login_required
def admin_reports_export(request):

    access = admin_superuser_required(request)

    if access:
        return access

    import csv

    response = HttpResponse(
        content_type="text/csv"
    )

    response["Content-Disposition"] = (
        'attachment; filename="application_report.csv"'
    )

    writer = csv.writer(response)

    writer.writerow([
        "Application ID",
        "Applicant",
        "Application Type",
        "Status",
        "Verification Status",
        "Barangay",
        "Municipality",
        "Province",
        "Date",
    ])

    # =========================================================
    # NEW
    # =========================================================

    applicants = Applicant.objects.select_related(
        "brgy"
    ).all()

    for applicant in applicants:

        writer.writerow([
            applicant.id,
            str(applicant),
            "New Registration",
            applicant.get_status_display(),
            applicant.get_verification_status_display(),
            applicant.brgy.name if applicant.brgy else "",
            applicant.municipality,
            applicant.province,
            applicant.date_joined,
        ])

    # =========================================================
    # UPDATE
    # =========================================================

    update_requests = ApplicantUpdateRequest.objects.select_related(
        "applicant",
        "brgy"
    ).all()

    for item in update_requests:

        writer.writerow([
            item.id,
            str(item.applicant),
            "Update Information",
            item.get_status_display(),
            item.applicant.get_verification_status_display(),
            item.brgy.name if item.brgy else "",
            item.municipality,
            item.province,
            item.requested_at,
        ])

    # =========================================================
    # TRANSFER
    # =========================================================

    transfer_requests = ApplicantTransferRequest.objects.select_related(
        "applicant",
        "new_brgy"
    ).all()

    for item in transfer_requests:

        writer.writerow([
            item.id,
            str(item.applicant),
            "Transfer",
            item.get_status_display(),
            item.applicant.get_verification_status_display(),
            item.new_brgy.name if item.new_brgy else "",
            item.new_municipality,
            item.new_province,
            item.requested_at,
        ])

    # =========================================================
    # REACTIVATION
    # =========================================================

    reactivation_requests = ApplicantReactivationRequest.objects.select_related(
        "applicant",
        "applicant__brgy"
    ).all()

    for item in reactivation_requests:

        writer.writerow([
            item.id,
            str(item.applicant),
            "Reactivation",
            item.get_status_display(),
            item.applicant.get_verification_status_display(),
            (
                item.applicant.brgy.name
                if item.applicant.brgy
                else ""
            ),
            item.applicant.municipality,
            item.applicant.province,
            item.requested_at,
        ])

    # =========================================================
    # REINSTATEMENT
    # =========================================================

    reinstatement_requests = ApplicantReinstatementRequest.objects.select_related(
        "applicant",
        "applicant__brgy"
    ).all()

    for item in reinstatement_requests:

        writer.writerow([
            item.id,
            str(item.applicant),
            "Reinstatement",
            item.get_status_display(),
            item.applicant.get_verification_status_display(),
            (
                item.applicant.brgy.name
                if item.applicant.brgy
                else ""
            ),
            item.applicant.municipality,
            item.applicant.province,
            item.requested_at,
        ])

    return response


@login_required()
def delete_application(request, id):

    application = get_object_or_404(Applicant, id=id)

    if request.method == "POST":
        application.delete()
        return redirect("admin-applications")

    return redirect("admin-applications")



@csrf_exempt
@require_POST
def save_fingerprint(request, applicant_id):
    """
    Receive a fingerprint image from the ESP32, validate it, convert
    it to PNG, and save it to the applicant's biometric record.

    Completion rule:
        COMPLETE when both left and right fingerprint images exist.

    Fingerprint templates are optional; all three applicant signatures are required
    for biometric image completion.
    """

    # --------------------------------------------------
    # 1. Validate the requested finger
    # --------------------------------------------------

    finger = request.POST.get("finger", "").strip().lower()

    if finger not in ("left", "right"):
        return JsonResponse({
            "success": False,
            "message": "Invalid finger. Use left or right.",
        }, status=400)

    # --------------------------------------------------
    # 2. Verify that the applicant exists
    # --------------------------------------------------

    try:
        applicant = Applicant.objects.get(pk=applicant_id)

    except Applicant.DoesNotExist:
        return JsonResponse({
            "success": False,
            "message": "Applicant not found.",
            "applicant_id": applicant_id,
        }, status=404)

    # --------------------------------------------------
    # 3. Get the uploaded fingerprint image
    # --------------------------------------------------

    uploaded_file = request.FILES.get("fingerprint")

    if uploaded_file is None:
        logger.warning(
            "Fingerprint upload missing: applicant=%s, finger=%s, "
            "POST fields=%s, FILES fields=%s",
            applicant_id,
            finger,
            list(request.POST.keys()),
            list(request.FILES.keys()),
        )

        return JsonResponse({
            "success": False,
            "message": "No fingerprint image was uploaded.",
            "expected_file_field": "fingerprint",
            "received_fields": list(request.FILES.keys()),
        }, status=400)

    # --------------------------------------------------
    # 4. Validate uploaded file size
    # --------------------------------------------------

    max_upload_size = 2 * 1024 * 1024  # 2 MB

    if uploaded_file.size <= 0:
        return JsonResponse({
            "success": False,
            "message": "The uploaded fingerprint image is empty.",
        }, status=400)

    if uploaded_file.size > max_upload_size:
        return JsonResponse({
            "success": False,
            "message": "Fingerprint image must not exceed 2 MB.",
            "received_bytes": uploaded_file.size,
        }, status=400)

    logger.info(
        "Fingerprint upload received: applicant=%s, finger=%s, "
        "filename=%s, content_type=%s, bytes=%s",
        applicant_id,
        finger,
        uploaded_file.name,
        uploaded_file.content_type,
        uploaded_file.size,
    )

    # --------------------------------------------------
    # 5. Decode and convert the image to PNG
    # --------------------------------------------------

    output = BytesIO()

    try:
        uploaded_file.seek(0)

        with Image.open(uploaded_file) as source:
            source.load()

            original_format = source.format
            original_width, original_height = source.size

            if original_width <= 0 or original_height <= 0:
                return JsonResponse({
                    "success": False,
                    "message": "The fingerprint image has invalid dimensions.",
                }, status=400)

            png_image = source.convert("L")

            image_width = png_image.width
            image_height = png_image.height

            png_image.save(output, format="PNG")
            png_data = output.getvalue()

    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
    ):
        logger.warning(
            "Invalid fingerprint image: applicant=%s, finger=%s",
            applicant_id,
            finger,
            exc_info=True,
        )

        return JsonResponse({
            "success": False,
            "message": (
                "The uploaded data is not a valid image or cannot be "
                "decoded. Upload a valid BMP, PNG, or JPEG image."
            ),
            "filename": uploaded_file.name,
            "content_type": uploaded_file.content_type,
            "received_bytes": uploaded_file.size,
        }, status=400)

    except Exception:
        logger.exception(
            "Unexpected image processing error: applicant=%s, finger=%s",
            applicant_id,
            finger,
        )

        return JsonResponse({
            "success": False,
            "message": "An unexpected error occurred while processing the image.",
        }, status=500)

    finally:
        output.close()

    # --------------------------------------------------
    # 6. Retrieve or create the biometric record
    # --------------------------------------------------

    try:
        biometric, created = ApplicantBiometric.objects.get_or_create(
            applicant=applicant
        )

    except Exception:
        logger.exception(
            "Could not retrieve or create biometric record: applicant=%s",
            applicant_id,
        )

        return JsonResponse({
            "success": False,
            "message": "Could not create or retrieve the biometric record.",
            "applicant_id": applicant_id,
        }, status=500)

    # --------------------------------------------------
    # 7. Remember the previous image
    # --------------------------------------------------

    if finger == "left":
        old_file_name = (
            biometric.left_finger.name
            if biometric.left_finger
            else ""
        )
    else:
        old_file_name = (
            biometric.right_finger.name
            if biometric.right_finger
            else ""
        )

    # --------------------------------------------------
    # 8. Save the new fingerprint image
    # --------------------------------------------------

    filename = (
        f"applicant_{applicant_id}_{finger}_fingerprint.png"
    )

    try:
        if finger == "left":
            biometric.left_finger.save(
                filename,
                ContentFile(png_data),
                save=False,
            )
        else:
            biometric.right_finger.save(
                filename,
                ContentFile(png_data),
                save=False,
            )

        biometric.save()

    except Exception:
        logger.exception(
            "Failed to save fingerprint image: applicant=%s, finger=%s",
            applicant_id,
            finger,
        )

        return JsonResponse({
            "success": False,
            "message": (
                "The fingerprint image was processed but could not be saved."
            ),
        }, status=500)

    # --------------------------------------------------
    # 9. Delete the old image after saving the replacement
    # --------------------------------------------------

    current_image_field = (
        biometric.left_finger
        if finger == "left"
        else biometric.right_finger
    )

    new_file_name = current_image_field.name

    if old_file_name and old_file_name != new_file_name:
        try:
            current_image_field.storage.delete(old_file_name)

        except Exception:
            logger.exception(
                "Could not delete previous fingerprint image: %s",
                old_file_name,
            )

    # --------------------------------------------------
    # 10. Check both saved fingerprint images
    # --------------------------------------------------

    biometric.refresh_from_db()

    left_image_saved = bool(
        biometric.left_finger and biometric.left_finger.name
    )
    right_image_saved = bool(
        biometric.right_finger and biometric.right_finger.name
    )

    # Templates are optional.
    left_template_saved = bool(biometric.left_finger_template)
    right_template_saved = bool(biometric.right_finger_template)

    # Completion requires both fingerprints and all three signature files.
    completed = capture_complete(biometric)

    # --------------------------------------------------
    # 11. Persist biometric completion flags
    # --------------------------------------------------

    biometric.biometrics_completed = completed
    biometric.completed = completed

    biometric.save(
        update_fields=[
            "biometrics_completed",
            "completed",
            "updated_at",
        ]
    )

    biometric.refresh_from_db()

    # --------------------------------------------------
    # 12. Persist and verify applicant verification status
    # --------------------------------------------------

    verification_status = (
        "VERIFIED" if completed else "BIOMETRICS_PENDING"
    )

    try:
        # Update directly in the database, bypassing model save()
        # overrides that might alter verification_status.
        Applicant.objects.filter(
            pk=applicant_id
        ).update(
            verification_status=verification_status
        )

        # Reload the actual persisted value.
        applicant.refresh_from_db()

        final_status = applicant.verification_status

        logger.info(
            "Applicant verification status persisted: "
            "applicant=%s, expected=%s, actual=%s",
            applicant_id,
            verification_status,
            final_status,
        )

        # Do not report success if the database value differs.
        if final_status != verification_status:
            logger.error(
                "Verification status mismatch: applicant=%s, "
                "expected=%s, actual=%s",
                applicant_id,
                verification_status,
                final_status,
            )

            return JsonResponse({
                "success": False,
                "message": (
                    "Fingerprint images were saved, but the applicant "
                    "verification status did not match the expected value."
                ),
                "applicant_id": applicant_id,
                "expected_verification_status": verification_status,
                "actual_verification_status": final_status,
            }, status=500)

    except Exception:
        logger.exception(
            "Failed to update applicant verification status: applicant=%s",
            applicant_id,
        )

        return JsonResponse({
            "success": False,
            "message": (
                "Fingerprint images were saved, but the applicant "
                "verification status could not be updated."
            ),
            "applicant_id": applicant_id,
        }, status=500)

    # --------------------------------------------------
    # 13. Get the saved image URL
    # --------------------------------------------------

    saved_image_field = (
        biometric.left_finger
        if finger == "left"
        else biometric.right_finger
    )

    try:
        image_url = saved_image_field.url

    except (ValueError, NotImplementedError):
        image_url = None

    # --------------------------------------------------
    # 14. Log final status
    # --------------------------------------------------

    logger.info(
        "Fingerprint saved: applicant=%s, finger=%s, "
        "left_image=%s, right_image=%s, completed=%s, "
        "verification_status=%s",
        applicant_id,
        finger,
        left_image_saved,
        right_image_saved,
        completed,
        final_status,
    )

    # --------------------------------------------------
    # 15. Prepare response message
    # --------------------------------------------------

    if completed:
        message = (
            "Both left and right fingerprint images are saved. "
            "Biometrics are COMPLETE."
        )
    else:
        missing_finger = (
            "right" if left_image_saved else "left"
        )

        message = (
            f"{finger.capitalize()} fingerprint saved successfully. "
            f"Waiting for the {missing_finger} fingerprint."
        )

    # --------------------------------------------------
    # 16. Return JSON response
    # --------------------------------------------------

    return JsonResponse({
        "success": True,
        "message": message,
        "applicant_id": applicant_id,
        "finger": finger,

        # Record information
        "biometric_record_created": created,

        # Saved image information
        "image_url": image_url,
        "image_format": "PNG",
        "original_format": original_format,
        "image_width": image_width,
        "image_height": image_height,
        "original_width": original_width,
        "original_height": original_height,
        "original_bytes": uploaded_file.size,
        "png_bytes": len(png_data),

        # Image status
        "left_image_saved": left_image_saved,
        "right_image_saved": right_image_saved,

        # Template status; not required for completion
        "left_template_saved": left_template_saved,
        "right_template_saved": right_template_saved,

        # Persisted completion status
        "biometrics_completed": biometric.biometrics_completed,
        "completed": biometric.completed,

        # Actual database verification status
        "verification_status": final_status,
        "verification_status_display": (
            applicant.get_verification_status_display()
        ),
    })



@csrf_exempt
@require_POST
def fingerprint_device_upload(request, applicant_id):
    applicant = get_object_or_404(Applicant, pk=applicant_id)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {"error": "Invalid JSON request."},
            status=400,
        )

    finger = str(data.get("finger", "")).lower().strip()
    template_b64 = data.get("template", "")

    if finger not in ("left", "right"):
        return JsonResponse(
            {"error": "finger must be left or right."},
            status=400,
        )

    if not isinstance(template_b64, str) or not template_b64:
        return JsonResponse(
            {"error": "A Base64 fingerprint template is required."},
            status=400,
        )

    if len(template_b64) > 16000:
        return JsonResponse(
            {"error": "Template is too large."},
            status=400,
        )

    # Validate that it is valid Base64 before saving
    try:
        template_bytes = base64.b64decode(
            template_b64,
            validate=True,
        )
    except (ValueError, base64.binascii.Error):
        return JsonResponse(
            {"error": "Invalid Base64 template."},
            status=400,
        )

    if not template_bytes or len(template_bytes) > 8192:
        return JsonResponse(
            {"error": "Invalid template length."},
            status=400,
        )

    try:
        with transaction.atomic():
            biometric, _ = ApplicantBiometric.objects.get_or_create(
                applicant=applicant
            )

            # Dynamically set either left_finger_template or right_finger_template
            field_name = f"{finger}_finger_template"
            setattr(biometric, field_name, template_b64)
            biometric.save()

        return JsonResponse({
            "success": True,
            "message": f"{finger.capitalize()} fingerprint template saved successfully.",
            "applicant_id": applicant_id,
            "finger": finger,
        }, status=200)

    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": f"Database save failed: {str(e)}",
        }, status=500)


@login_required
@require_POST
def start_fingerprint_capture(request, applicant_id):
    if not request.user.is_staff:
        return JsonResponse(
            {
                "success": False,
                "error": "Permission denied.",
            },
            status=403,
        )

    finger = request.POST.get("finger", "").strip().lower()

    if finger not in ("left", "right"):
        return JsonResponse(
            {
                "success": False,
                "error": "Invalid finger. Use left or right.",
            },
            status=400,
        )

    applicant = get_object_or_404(Applicant, pk=applicant_id)

    with transaction.atomic():
        active_request = (
            FingerprintCaptureRequest.objects
            .select_for_update()
            .filter(
                applicant=applicant,
                finger=finger,
                status__in=["pending", "capturing"],
            )
            .order_by("-created_at")
            .first()
        )

        if active_request:
            # Reuse the active request so the staff member can retry.
            active_request.status = "pending"
            active_request.message = (
                f"Capture restarted. Waiting for the device to capture "
                f"the {finger} fingerprint."
            )
            active_request.save(
                update_fields=["status", "message", "updated_at"]
            )

            capture_request = active_request
            reused_request = True

            logger.info(
                "Fingerprint capture restarted: request=%s applicant=%s finger=%s",
                capture_request.id,
                applicant.id,
                finger,
            )

        else:
            capture_request = FingerprintCaptureRequest.objects.create(
                applicant=applicant,
                finger=finger,
                status="pending",
                message=f"Waiting for device to capture {finger} fingerprint.",
            )
            reused_request = False

            logger.info(
                "Fingerprint capture request created: request=%s applicant=%s finger=%s",
                capture_request.id,
                applicant.id,
                finger,
            )

    return JsonResponse({
        "success": True,
        "request_id": capture_request.id,
        "applicant_id": applicant.id,
        "finger": capture_request.finger,
        "status": capture_request.status,
        "message": capture_request.message,
        "reused_request": reused_request,
    })




@csrf_exempt
@require_GET
def fingerprint_device_next(request):
    # Prototype endpoint: no device token, as requested.
    with transaction.atomic():
        capture_request = (
            FingerprintCaptureRequest.objects
            .select_for_update()
            .filter(status="pending")
            .order_by("created_at")
            .first()
        )

        if capture_request is None:
            return JsonResponse({"command": None})

        capture_request.status = "capturing"
        capture_request.message = "Device accepted capture request."
        capture_request.save(
            update_fields=["status", "message", "updated_at"]
        )

        return JsonResponse({
            "command": "capture",
            "request_id": capture_request.id,
            "applicant_id": capture_request.applicant_id,
            "finger": capture_request.finger,
        })


@csrf_exempt
@require_POST
def fingerprint_device_complete(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {"success": False, "error": "Invalid JSON."},
            status=400,
        )

    request_id = data.get("request_id")
    success = data.get("success")
    message = str(data.get("message", ""))[:255]

    if (
        isinstance(request_id, bool)
        or not isinstance(request_id, int)
        or request_id <= 0
    ):
        return JsonResponse(
            {"success": False, "error": "Invalid request_id."},
            status=400,
        )

    if not isinstance(success, bool):
        return JsonResponse(
            {
                "success": False,
                "error": "success must be true or false.",
            },
            status=400,
        )

    with transaction.atomic():
        capture_request = get_object_or_404(
            FingerprintCaptureRequest.objects.select_for_update(),
            pk=request_id,
        )

        if capture_request.status != "capturing":
            logger.warning(
                "Fingerprint completion rejected: request=%s status=%s",
                capture_request.id,
                capture_request.status,
            )
            return JsonResponse(
                {
                    "success": False,
                    "error": "Capture request is not active.",
                    "request_id": capture_request.id,
                    "status": capture_request.status,
                },
                status=409,
            )

        capture_request.status = "completed" if success else "failed"
        capture_request.message = message or (
            "Fingerprint capture completed successfully."
            if success
            else "Fingerprint capture failed."
        )
        capture_request.save(
            update_fields=["status", "message", "updated_at"]
        )

    logger.info(
        "Fingerprint completion received: request=%s applicant=%s "
        "finger=%s status=%s",
        capture_request.id,
        capture_request.applicant_id,
        capture_request.finger,
        capture_request.status,
    )

    return JsonResponse({
        "success": True,
        "request_id": capture_request.id,
        "applicant_id": capture_request.applicant_id,
        "finger": capture_request.finger,
        "status": capture_request.status,
        "message": capture_request.message,
    })



@login_required
@require_GET
def fingerprint_capture_status(request, request_id):
    if not request.user.is_staff:
        return JsonResponse(
            {
                "success": False,
                "error": "Permission denied.",
            },
            status=403,
        )

    capture_request = get_object_or_404(
        FingerprintCaptureRequest,
        pk=request_id,
    )

    return JsonResponse({
        "success": True,
        "request_id": capture_request.id,
        "applicant_id": capture_request.applicant_id,
        "finger": capture_request.finger,
        "status": capture_request.status,
        "message": capture_request.message,
        "created_at": capture_request.created_at.isoformat(),
        "updated_at": capture_request.updated_at.isoformat(),
    })
