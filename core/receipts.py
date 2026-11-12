"""Persistent receipts available only after verified biometric capture."""
from secrets import randbelow
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_GET, require_POST
from django.utils import timezone
from Applicants.models import Applicant, ApplicantBiometric, AcknowledgmentReceipt
from .biometric_state import capture_complete, settle_legacy_round
from .receipt_rendering import render_receipt

@require_GET
def acknowledgment_receipt(request, applicant_id, receipt_id=None):
    from .views import admin_superuser_required
    from Applicants.application_types import APPLICATION_TYPE_LABELS
    access = admin_superuser_required(request)
    if access:
        return access
    applicant = get_object_or_404(Applicant, pk=applicant_id)
    if receipt_id is not None:
        # A receipt issued for an earlier verification round; reprint it as issued.
        receipt = get_object_or_404(AcknowledgmentReceipt, pk=receipt_id, applicant=applicant)
    else:
        biometric = ApplicantBiometric.objects.filter(applicant=applicant).first()
        if not biometric or applicant.verification_status != "VERIFIED" or not biometric.completed or not biometric.biometrics_completed or not capture_complete(biometric):
            return redirect("admin-applicant-biometric", applicant_id=applicant.pk)
        # One receipt per verification round (first registration or each approved application).
        with transaction.atomic():
            biometric = settle_legacy_round(ApplicantBiometric.objects.select_for_update().get(pk=biometric.pk))
            round_filter = {"applicant": applicant, "application_type": biometric.application_type,
                            "application_request_id": biometric.application_request_id}
            receipt = AcknowledgmentReceipt.objects.filter(**round_filter).first()
            if receipt is None:
                details = {"lastname": applicant.lastname, "firstname": applicant.firstname, "middlename": applicant.middlename, "receipt_date": timezone.localdate().isoformat(), "officer": request.user.get_full_name() or request.user.get_username(), "application_type": APPLICATION_TYPE_LABELS.get(biometric.application_type, applicant.get_application_type_display())}
                for attempt in range(10):
                    try:
                        with transaction.atomic():
                            receipt = AcknowledgmentReceipt.objects.create(**round_filter, application_number=str(100_000_000_000 + randbelow(900_000_000_000)), details=details, issued_by=request.user)
                        break
                    except IntegrityError:
                        if attempt == 9:
                            raise
    values = dict(receipt.details, application_no=receipt.application_number)
    from .models import ReceiptSettings
    settings = ReceiptSettings.objects.filter(pk=1).first()
    if settings is not None:
        values['officer'] = settings.officer_name
    response = render_receipt(request, values, values["application_type"], applicant_id=applicant_id)
    response["Cache-Control"] = "private, no-store"
    return response


@require_POST
def save_receipt_settings(request, applicant_id):
    from .views import admin_superuser_required
    from .models import ReceiptSettings
    from django.contrib import messages
    access = admin_superuser_required(request)
    if access:
        return access
    get_object_or_404(Applicant, pk=applicant_id)
    name = request.POST.get('officer_name', '').strip()
    if len(name) > 100:
        messages.error(request, 'Officer name must be at most 100 characters.')
    else:
        ReceiptSettings.objects.update_or_create(pk=1, defaults={'officer_name': name})
        messages.success(request, 'Receipt officer name updated.')
    return redirect('acknowledgment-receipt', applicant_id=applicant_id)
