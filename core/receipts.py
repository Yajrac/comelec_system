"""Persistent receipts available only after verified biometric capture."""
from secrets import randbelow
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_GET
from django.utils import timezone
from Applicants.models import Applicant, ApplicantBiometric, AcknowledgmentReceipt
from .biometric_state import capture_complete
from .receipt_rendering import render_receipt

@require_GET
def acknowledgment_receipt(request, applicant_id):
    from .views import admin_superuser_required
    access = admin_superuser_required(request)
    if access:
        return access
    applicant = get_object_or_404(Applicant, pk=applicant_id)
    biometric = ApplicantBiometric.objects.filter(applicant=applicant).first()
    if not biometric or applicant.verification_status != "VERIFIED" or not biometric.completed or not biometric.biometrics_completed or not capture_complete(biometric):
        return redirect("admin-applicant-biometric", applicant_id=applicant.pk)
    receipt = AcknowledgmentReceipt.objects.filter(applicant=applicant).first()
    if receipt is None:
        details = {"lastname": applicant.lastname, "firstname": applicant.firstname, "middlename": applicant.middlename, "receipt_date": timezone.localdate().isoformat(), "officer": request.user.get_full_name() or request.user.get_username(), "application_type": applicant.get_application_type_display()}
        for attempt in range(10):
            try:
                with transaction.atomic():
                    receipt, created = AcknowledgmentReceipt.objects.get_or_create(applicant=applicant, defaults={"application_number": str(100_000_000_000 + randbelow(900_000_000_000)), "details": details, "issued_by": request.user})
                break
            except IntegrityError:
                if attempt == 9:
                    raise
    values = dict(receipt.details, application_no=receipt.application_number)
    response = render_receipt(request, values, values["application_type"])
    response["Cache-Control"] = "private, no-store"
    return response
