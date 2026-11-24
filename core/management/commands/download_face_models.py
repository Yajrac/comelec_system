"""Download and check the face match model files (run once per deploy, before turning face match on)."""
import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Download the ArcFace model into FACE_MODELS_DIR and run one test comparison."

    def handle(self, *args, **options):
        from Applicants.face_match import FaceEngineUnavailable, MODEL_NAME, _deepface

        settings.FACE_MODELS_DIR.mkdir(parents=True, exist_ok=True)
        try:
            DeepFace, cv2, numpy = _deepface()
        except FaceEngineUnavailable:
            raise CommandError("DeepFace is not installed. Run: pip install -r requirements.txt")
        self.stdout.write(f"Model folder: {settings.FACE_MODELS_DIR}")
        started = time.time()
        DeepFace.build_model(MODEL_NAME)
        blank = numpy.full((160, 160, 3), 127, dtype=numpy.uint8)
        DeepFace.represent(blank, model_name=MODEL_NAME, detector_backend="skip", enforce_detection=False)
        self.stdout.write(self.style.SUCCESS(f"ArcFace is ready ({time.time() - started:.1f}s)."))
