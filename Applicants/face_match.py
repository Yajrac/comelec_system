"""Compare the New Registration selfie with the photo on the uploaded ID.

Runs on this server with DeepFace (ArcFace embeddings, OpenCV face detection): no image leaves the
server. Only for documents with a photo (a PSA birth certificate has none). The ID may be photographed
sideways, so it is turned until an upright face (both eyes found) appears. Off unless FACE_MATCH_ENABLED.
"""
import hashlib
import logging
import os

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .document_check import MAX_FILE_SIZE, _mime_type
from .id_types import VALID_ID_CODES
from .models import FaceMatch

logger = logging.getLogger(__name__)

NO_PHOTO_TYPES = {"PSA_BIRTH_CERTIFICATE"}
BLOCKING = {"not_matched", "no_face", "unclear"}
# A face that could not be seen twice is let through for the office to review. A clearly different
# face (not_matched) is never let through: the applicant retakes it or visits the office.
RETRYABLE = {"no_face", "unclear"}
FAILED = {"not_matched", "no_face", "unclear", "flagged"}
RETRY_WINDOW_MINUTES = 60
ENGINE = "deepface-arcface-opencv-v1"  # readings from another engine are not reused
MODEL_NAME = "ArcFace"

MESSAGES = {
    "matched": "Your selfie matches the photo on your ID.",
    "not_matched": ("Your selfie does not match the photo on your ID. Retake your selfie facing the camera in good light. "
                    "If your ID photo is old or unclear, please visit the registration office."),
    "flagged": "We still could not see your face clearly. You can continue; the office will compare your selfie with your ID.",
    "no_face": "We could not see your face clearly. Retake your selfie facing the camera in good light.",
    "unclear": "Your selfie is too dark or blurry. Retake it in good light, facing the camera.",
    "unsure": "Your selfie could not be compared with your ID. You can continue; the office will compare them.",
    "unavailable": "Face comparison is unavailable right now. You can continue; the office will compare them.",
}


class FaceEngineUnavailable(Exception):
    """DeepFace is not installed, the model files are missing, or the images cannot be read."""


def enabled():
    return settings.FACE_MATCH_ENABLED


def has_photo(id_type):
    return id_type in VALID_ID_CODES and id_type not in NO_PHOTO_TYPES


def _read(uploaded):
    data = uploaded.read(MAX_FILE_SIZE + 1)
    uploaded.seek(0)
    return data


# ---------------------------------------------------------------- engine (DeepFace)

def _deepface():
    """Import DeepFace with its model files kept in FACE_MODELS_DIR (downloaded by download_face_models)."""
    os.environ.setdefault("DEEPFACE_HOME", str(settings.FACE_MODELS_DIR))
    try:
        import cv2
        import numpy
        from deepface import DeepFace
    except ImportError as error:
        raise FaceEngineUnavailable("not installed") from error
    return DeepFace, cv2, numpy


def _largest_face(image, rotations, upright_only):
    """Largest detected face as a BGR uint8 array, trying each rotation; None when there is none."""
    DeepFace, cv2, numpy = _deepface()
    best = None
    for code in rotations:
        turned = image if code is None else cv2.rotate(image, code)
        try:
            faces = DeepFace.extract_faces(turned, detector_backend="opencv", enforce_detection=True, align=True)
        except ValueError:  # no face in this rotation
            continue
        for face in faces:
            area = face["facial_area"]
            eyes = bool(area.get("left_eye") and area.get("right_eye"))
            if upright_only and not eyes:
                continue  # an upside-down or sideways face gives a meaningless comparison
            score = (eyes, area["w"] * area["h"], face["confidence"])
            if best is None or score > best[0]:
                best = (score, face["face"])
    if best is None:
        return None
    # extract_faces returns RGB floats 0-1; ArcFace expects a contiguous BGR image.
    return numpy.ascontiguousarray((best[1] * 255).astype("uint8")[:, :, ::-1])


def read_faces(selfie_data, document_data):
    """Find both faces and measure how far apart they are (ArcFace cosine distance; lower = more alike)."""
    DeepFace, cv2, numpy = _deepface()
    decode = lambda data: cv2.imdecode(numpy.frombuffer(data, numpy.uint8), cv2.IMREAD_COLOR)
    selfie_image, document_image = decode(selfie_data), decode(document_data)
    if selfie_image is None or document_image is None:
        raise FaceEngineUnavailable("unreadable image")
    try:
        selfie_face = _largest_face(selfie_image, (None,), upright_only=False)  # selfies are upright
        document_face = _largest_face(document_image, (None, cv2.ROTATE_90_CLOCKWISE,
                                                       cv2.ROTATE_90_COUNTERCLOCKWISE, cv2.ROTATE_180),
                                      upright_only=True)
        reading = {"selfie_has_face": selfie_face is not None, "document_has_face": document_face is not None,
                   "distance": None, "engine": ENGINE}
        if selfie_face is not None and document_face is not None:
            embed = lambda face: numpy.array(DeepFace.represent(
                face, model_name=MODEL_NAME, detector_backend="skip", enforce_detection=False)[0]["embedding"])
            a, b = embed(selfie_face), embed(document_face)
            reading["distance"] = round(1 - float(a @ b / (numpy.linalg.norm(a) * numpy.linalg.norm(b))), 4)
    except FaceEngineUnavailable:
        raise
    except Exception as error:  # model file missing, out of memory, bad image: never block the applicant
        logger.error("Face match unavailable: %s", type(error).__name__)
        raise FaceEngineUnavailable("error") from error
    return reading


def evaluate(reading):
    """matched (close), not_matched (far), unsure (in between, or no face on the ID), no_face (selfie)."""
    if not reading["selfie_has_face"]:
        return "no_face"
    if not reading["document_has_face"] or reading.get("distance") is None:
        return "unsure"
    if reading["distance"] <= settings.FACE_MATCH_MAX_DISTANCE:
        return "matched"
    if reading["distance"] >= settings.FACE_MATCH_REJECT_DISTANCE:
        return "not_matched"
    return "unsure"


def _failed_recently(base):
    """An earlier failed selfie (this engine, same document, last hour) other than this one."""
    from datetime import timedelta
    from django.utils import timezone
    earlier = FaceMatch.objects.filter(
        document_digest=base["document_digest"], status__in=FAILED,
        created_at__gte=timezone.now() - timedelta(minutes=RETRY_WINDOW_MINUTES),
    ).exclude(selfie_digest=base["selfie_digest"])[:20]
    return any((check.ai_result or {}).get("engine") == ENGINE for check in earlier)


def compare(selfie, document, id_type):
    """Always returns a saved FaceMatch for this selfie and document."""
    selfie_data, document_data = _read(selfie), _read(document)
    base = {"selfie_digest": hashlib.sha256(selfie_data).hexdigest(),
            "document_digest": hashlib.sha256(document_data).hexdigest()}
    if not has_photo(id_type):
        return FaceMatch.objects.create(status="not_applicable", **base)

    previous = next((check for check in FaceMatch.objects.filter(ai_checked=True, **base)[:10]
                     if (check.ai_result or {}).get("engine") == ENGINE), None)
    if previous:
        reading, model_name = previous.ai_result, previous.model_name
    else:
        try:
            if _mime_type(selfie_data) not in {"image/jpeg", "image/png"} \
                    or _mime_type(document_data) not in {"image/jpeg", "image/png"} \
                    or max(len(selfie_data), len(document_data)) > MAX_FILE_SIZE:
                raise FaceEngineUnavailable("unsupported file")  # e.g. a PDF: the office compares
            reading, model_name = read_faces(selfie_data, document_data), MODEL_NAME
        except FaceEngineUnavailable:
            return FaceMatch.objects.create(status="unavailable", **base)

    status = evaluate(reading)
    if status in RETRYABLE and _failed_recently(base):
        status = "flagged"  # face still not seen: let the applicant continue, the office reviews it
    return FaceMatch.objects.create(status=status, ai_checked=True, ai_result=reading, model_name=model_name, **base)


def enforce(request, selfie, document, id_type):
    """Check a New Registration submission. Returns (check, error_message); (None, None) when it does not apply."""
    if not enabled() or not selfie or not document:
        return None, None
    check = compare(selfie, document, id_type)
    if check.status not in BLOCKING:
        return check, None
    officer = getattr(request, "user", None)
    if (getattr(request, "walk_in_base", None) and officer is not None and officer.is_authenticated
            and officer.is_superuser and request.POST.get("officer_verified") == "1"):
        check.status, check.officer = "override", officer
        check.save(update_fields=["status", "officer"])
        return check, None
    return check, MESSAGES[check.status]


def link(check, record_id):
    if check is not None:
        check.record_id = record_id
        check.save(update_fields=["record_id"])


def latest_for(record_id):
    return FaceMatch.objects.filter(record_id=record_id).first()


@csrf_exempt
@require_POST
def face_check_view(request):
    """Compare the selfie with the ID before submitting (New Registration)."""
    if not enabled():
        return JsonResponse({"status": "disabled"})
    selfie, document = request.FILES.get("photo"), request.FILES.get("valid_id_document")
    if not selfie or not document or max(selfie.size, document.size) > MAX_FILE_SIZE:
        return JsonResponse({"status": "error", "message": "Take a selfie and upload your document first."}, status=400)
    check = compare(selfie, document, request.POST.get("valid_id_type", ""))
    return JsonResponse({"status": check.status, "message": MESSAGES.get(check.status, "")})
