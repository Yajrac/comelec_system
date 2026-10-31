"""Signature capture stays compatible with devices posting session_id + PNG."""
import base64
import binascii
import json
import logging
import uuid
from io import BytesIO
from PIL import Image
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from Applicants.models import Applicant, ApplicantBiometric, SignatureSession
from .biometric_state import SIGNATURE_FIELDS, file_exists, signatures_complete, capture_complete, sync_completion

logger = logging.getLogger(__name__)

@login_required
@require_POST
def start_signature_session(request, applicant_id):
    if not request.user.is_superuser:
        return JsonResponse({"success": False, "message": "Administrator access required."}, status=403)
    try:
        data = json.loads(request.body) if request.content_type == "application/json" else request.POST
        slot = data.get("signature_slot", 1)
        if isinstance(slot, bool) or str(slot) not in {"1", "2", "3"}:
            raise ValueError()
        slot = int(slot)
    except (ValueError, TypeError, AttributeError, UnicodeDecodeError):
        return JsonResponse({"success": False, "message": "Select signature slot 1, 2, or 3."}, status=400)
    with transaction.atomic():
        applicant = get_object_or_404(Applicant.objects.select_for_update(), pk=applicant_id)
        SignatureSession.objects.filter(applicant=applicant, status=SignatureSession.STATUS_WAITING).update(status=SignatureSession.STATUS_CANCELLED, cancelled_at=timezone.now())
        session = SignatureSession.objects.create(applicant=applicant, officer=request.user, signature_slot=slot)
    return JsonResponse({"success": True, "session_id": str(session.session_id), "applicant_id": applicant.id, "applicant_name": str(applicant), "signature_slot": slot, "status": session.status})

@require_GET
def get_waiting_signature_session(request):
    session = SignatureSession.objects.filter(status=SignatureSession.STATUS_WAITING).select_related("applicant").order_by("-created_at").first()
    return JsonResponse({"success": True, "session": None if session is None else {"session_id": str(session.session_id), "applicant_id": session.applicant_id, "applicant_name": str(session.applicant), "signature_slot": session.signature_slot, "status": session.status}})

@csrf_exempt
@require_POST
def complete_signature_session(request):
    try:
        body = json.loads(request.body)
        session_id = uuid.UUID(str(body.get("session_id")))
        signature = body.get("signature")
        if not isinstance(signature, str) or not signature.startswith("data:image/png;base64,") or len(signature) > 7 * 1024 * 1024:
            raise ValueError()
        image_data = base64.b64decode(signature.split(",", 1)[1], validate=True)
        if len(image_data) > 5 * 1024 * 1024:
            raise ValueError()
        with Image.open(BytesIO(image_data)) as image:
            if image.format != "PNG" or not 1 <= image.width <= 4096 or not 1 <= image.height <= 4096:
                raise ValueError()
            image.verify()
    except (ValueError, TypeError, AttributeError, UnicodeDecodeError, binascii.Error, OSError, Image.DecompressionBombError):
        return JsonResponse({"success": False, "message": "Provide a valid session ID and PNG signature (maximum 5 MB, 4096 pixels per side)."}, status=400)
    saved_file = None
    try:
        with transaction.atomic():
            initial = SignatureSession.objects.filter(session_id=session_id).values("applicant_id").first()
            if not initial:
                return JsonResponse({"success": False, "message": "Signature session not found."}, status=404)
            Applicant.objects.select_for_update().get(pk=initial["applicant_id"])
            session = SignatureSession.objects.select_for_update().get(session_id=session_id)
            if session.status != SignatureSession.STATUS_WAITING:
                return JsonResponse({"success": False, "message": "This signature session is no longer available."}, status=400)
            biometric, _ = ApplicantBiometric.objects.get_or_create(applicant_id=session.applicant_id)
            field = getattr(biometric, SIGNATURE_FIELDS[session.signature_slot])
            field.save(f"applicant_{session.applicant_id}_signature_{session.signature_slot}_{session.session_id}.png", ContentFile(image_data), save=False)
            saved_file = (field.storage, field.name)
            biometric.captured_at = timezone.now()
            biometric.save()
            complete = sync_completion(biometric)
            session.status = SignatureSession.STATUS_COMPLETED
            session.completed_at = timezone.now()
            session.save(update_fields=["status", "completed_at"])
        return JsonResponse({"success": True, "message": "Signature saved successfully.", "session_id": str(session.session_id), "applicant_id": session.applicant_id, "signature_slot": session.signature_slot, "signature_url": field.url, "signatures_complete": signatures_complete(biometric), "biometrics_completed": complete})
    except Exception:
        if saved_file:
            try:
                saved_file[0].delete(saved_file[1])
            except OSError:
                logger.error("Could not clean up an uncommitted signature file.")
        logger.exception("Signature could not be saved.")
        return JsonResponse({"success": False, "message": "Unable to save the signature. Please try again."}, status=500)

@require_GET
def signature_session_status(request, session_id):
    session = get_object_or_404(SignatureSession.objects.select_related("applicant"), session_id=session_id)
    biometric = ApplicantBiometric.objects.filter(applicant_id=session.applicant_id).first()
    field = getattr(biometric, SIGNATURE_FIELDS[session.signature_slot]) if biometric else None
    captured = session.status == SignatureSession.STATUS_COMPLETED and file_exists(field)
    return JsonResponse({"success": True, "session_id": str(session.session_id), "status": session.status, "applicant_id": session.applicant_id, "applicant_name": str(session.applicant), "signature_slot": session.signature_slot, "signature_captured": captured, "signature_url": field.url if captured else None, "signatures_complete": signatures_complete(biometric) if biometric else False, "biometrics_completed": capture_complete(biometric) if biometric else False})
