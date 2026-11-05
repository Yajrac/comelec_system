"""Replay-safe mobile submissions when a connection drops after the server saves."""
import json
import hashlib
import re
from functools import wraps

from django.db import IntegrityError, transaction
from django.http import JsonResponse
from Applicants.models import MobileSubmissionReceipt, RegistrationIdentityLock


def mobile_submission(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if request.method != "POST":
            return view(request, *args, **kwargs)
        try:
            data = json.loads(request.body) if request.content_type == "application/json" else request.POST
        except (ValueError, UnicodeDecodeError):
            return view(request, *args, **kwargs)
        reference = data.get("client_reference")
        if reference is None:
            return view(request, *args, **kwargs)
        if not isinstance(reference, str) or not re.fullmatch(r"[A-Za-z0-9-]{10,100}", reference):
            return JsonResponse({"success": False, "error": "Invalid mobile submission reference."}, status=400)

        def replay(receipt):
            if receipt.endpoint != view.__name__:
                return JsonResponse({"success": False, "error": "This submission reference belongs to another service."}, status=409)
            return JsonResponse(receipt.response, status=receipt.status_code)

        receipt = MobileSubmissionReceipt.objects.filter(client_reference=reference).first()
        if receipt:
            return replay(receipt)
        try:
            with transaction.atomic():
                key = hashlib.sha256(('receipt:' + reference).encode()).hexdigest()
                RegistrationIdentityLock.objects.get_or_create(key=key)
                RegistrationIdentityLock.objects.select_for_update().get(key=key)
                receipt = MobileSubmissionReceipt.objects.filter(client_reference=reference).first()
                if receipt:
                    return replay(receipt)
                response = view(request, *args, **kwargs)
                if 200 <= response.status_code < 300:
                    MobileSubmissionReceipt.objects.create(client_reference=reference, endpoint=view.__name__,
                        response=json.loads(response.content), status_code=response.status_code)
                return response
        except IntegrityError:
            receipt = MobileSubmissionReceipt.objects.filter(client_reference=reference).first()
            if receipt:
                return replay(receipt)
            raise
    return wrapped
