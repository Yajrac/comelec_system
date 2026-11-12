"""Shared completion rules for device and administrator capture paths."""
from Applicants.models import Applicant

SIGNATURE_FIELDS = {1: "applicant_signature", 2: "applicant_signature_2", 3: "applicant_signature_3"}


def file_exists(field):
    try:
        return bool(field and field.name and field.storage.exists(field.name))
    except (OSError, ValueError):
        return False


def signatures_complete(biometric):
    return all(file_exists(getattr(biometric, field)) for field in SIGNATURE_FIELDS.values())


def capture_complete(biometric):
    return file_exists(biometric.left_finger) and file_exists(biometric.right_finger) and signatures_complete(biometric)


def sync_completion(biometric):
    complete = capture_complete(biometric)
    biometric.completed = complete
    biometric.biometrics_completed = complete
    biometric.save(update_fields=["completed", "biometrics_completed", "updated_at"])
    Applicant.objects.filter(pk=biometric.applicant_id).update(verification_status="VERIFIED" if complete else "BIOMETRICS_PENDING")
    return complete


CAPTURE_FIELDS = ("left_finger", "left_finger_template", "right_finger", "right_finger_template",
                  "applicant_signature", "applicant_signature_2", "applicant_signature_3")


def restart_biometrics(applicant, application_type, request_id):
    """Start a new capture round after an approved application.

    The previous capture is kept as BiometricHistory (files stay where they are; only the
    references move), and the applicant must be captured again before being verified.
    """
    from django.db import transaction
    from Applicants.models import ApplicantBiometric, BiometricHistory
    with transaction.atomic():
        biometric, _ = ApplicantBiometric.objects.select_for_update().get_or_create(applicant=applicant)
        if any(getattr(biometric, name) for name in CAPTURE_FIELDS):
            BiometricHistory.objects.create(
                applicant=applicant,
                **{name: getattr(biometric, name) for name in CAPTURE_FIELDS},
                was_completed=biometric.completed,
                captured_at=biometric.captured_at,
                application_type=biometric.application_type,
                application_request_id=biometric.application_request_id,
                replaced_by_type=application_type,
                replaced_by_request_id=request_id,
            )
        for name in CAPTURE_FIELDS:
            setattr(biometric, name, None)
        biometric.completed = False
        biometric.biometrics_completed = False
        biometric.captured_at = None
        biometric.application_type = application_type
        biometric.application_request_id = request_id
        biometric.save()
        Applicant.objects.filter(pk=applicant.pk).update(verification_status="BIOMETRICS_PENDING")
    return biometric


def settle_legacy_round(biometric):
    """Requests approved before capture rounds were recorded left the round at NEW.

    If so, the latest approved request is the application this verification belongs to,
    so its receipt shows the right type (e.g. Transfer instead of Registration).
    """
    if biometric.application_type != "NEW":
        return biometric
    from Applicants.models import (ApplicantUpdateRequest, ApplicantTransferRequest,
                                   ApplicantReactivationRequest, ApplicantReinstatementRequest)
    latest = None
    for code, model in (("UPDATE", ApplicantUpdateRequest), ("TRANSFER", ApplicantTransferRequest),
                        ("REACTIVATION", ApplicantReactivationRequest), ("REINSTATEMENT", ApplicantReinstatementRequest)):
        for request in model.objects.filter(applicant_id=biometric.applicant_id, status="APPROVED"):
            when = request.reviewed_at or request.requested_at
            if latest is None or when > latest[0]:
                latest = (when, code, request.pk)
    if latest:
        biometric.application_type, biometric.application_request_id = latest[1], latest[2]
        biometric.save(update_fields=["application_type", "application_request_id", "updated_at"])
    return biometric
