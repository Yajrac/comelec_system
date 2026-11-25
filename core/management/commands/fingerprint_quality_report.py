"""Show the quality score of every saved thumbprint (numbers only), to set FINGERPRINT_MIN_COVERAGE."""
from django.conf import settings
from django.core.management.base import BaseCommand
from PIL import Image

from Applicants.models import ApplicantBiometric
from core.fingerprint_quality import assess


class Command(BaseCommand):
    help = "List coverage and result for saved thumbprints (no names or images are shown)."

    def handle(self, *args, **options):
        self.stdout.write(f"Minimum coverage: {settings.FINGERPRINT_MIN_COVERAGE}%")
        counts = {"accepted": 0, "rejected": 0, "unreadable": 0}
        for biometric in ApplicantBiometric.objects.order_by("applicant_id"):
            for side in ("left", "right"):
                field = getattr(biometric, f"{side}_finger")
                if not field:
                    continue
                try:
                    with field.open("rb") as handle, Image.open(handle) as image:
                        result = assess(image)
                except Exception:
                    counts["unreadable"] += 1
                    self.stdout.write(f"applicant {biometric.applicant_id:>5} {side:5}  unreadable")
                    continue
                counts["accepted" if result["ok"] else "rejected"] += 1
                verdict = "accepted" if result["ok"] else "REJECTED"
                self.stdout.write(f"applicant {biometric.applicant_id:>5} {side:5}  coverage {result['coverage']}%  {verdict}")
        self.stdout.write(self.style.SUCCESS(
            f"Accepted {counts['accepted']}, rejected {counts['rejected']}, unreadable {counts['unreadable']}."))
