"""Optional profile details shared by registration applications."""
from pathlib import Path
import warnings
import uuid

from django.core.exceptions import ValidationError
from django.utils import timezone
from PIL import Image, UnidentifiedImageError

SUFFIX_CHOICES = [(value, value) for value in ("Jr.", "Sr.", "II", "III", "IV", "V")]


def photo_upload_path(instance, filename):
    now = timezone.localtime(timezone.now(), timezone.get_fixed_timezone(480))
    extension = Path(filename).suffix.lower()
    return f"applicant_photos/{now:%Y/%m}/{now:%Y-%m-%d_%H-%M-%S-%f}_{uuid.uuid4().hex[:8]}{extension}"


def validate_photo(upload):
    if upload.size > 5 * 1024 * 1024:
        raise ValidationError("Photo must be 5 MB or smaller.")
    extension = Path(upload.name).suffix.lower()
    if extension not in {".jpg", ".jpeg", ".png"}:
        raise ValidationError("Upload a JPG or PNG photo.")
    position = upload.tell()
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(upload) as image:
                expected = "PNG" if extension == ".png" else "JPEG"
                if image.format != expected:
                    raise ValidationError("Photo contents do not match the file extension.")
                image.verify()
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError,
            Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ValidationError("Upload a valid JPG or PNG image.")
    finally:
        upload.seek(position)


def profile_values(request, applicant=None):
    """Keep existing values for older clients that do not submit this section."""
    submitted = request.POST.get("profile_details_provided") == "1"
    values = {
        "suffix": request.POST.get("suffix", "").strip() if submitted else getattr(applicant, "suffix", ""),
        "is_indigenous": request.POST.get("is_indigenous") == "on" if submitted else getattr(applicant, "is_indigenous", False),
        "is_illiterate": request.POST.get("is_illiterate") == "on" if submitted else getattr(applicant, "is_illiterate", False),
        "photo": request.FILES.get("photo") or (applicant.photo.name if applicant and applicant.photo else ""),
    }
    if applicant is not None:
        values["profile_details_provided"] = submitted
    return values


def apply_profile_details(application, applicant):
    if application.profile_details_provided:
        for field in ("suffix", "is_indigenous", "is_illiterate", "photo"):
            setattr(applicant, field, getattr(application, field))
