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
