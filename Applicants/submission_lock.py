import hashlib
import json
from functools import wraps

from django.db import transaction
from .models import RegistrationIdentityLock


def registration_identity_lock(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if request.method != 'POST':
            return view(request, *args, **kwargs)
        try:
            data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
            identity = [str(data.get(name, '')).strip().casefold()
                        for name in ('lastname', 'firstname', 'middlename', 'birthdate')]
        except (ValueError, AttributeError, UnicodeDecodeError):
            return view(request, *args, **kwargs)
        key = hashlib.sha256(json.dumps(identity).encode()).hexdigest()
        with transaction.atomic():
            RegistrationIdentityLock.objects.get_or_create(key=key)
            RegistrationIdentityLock.objects.select_for_update().get(key=key)
            return view(request, *args, **kwargs)
    return wrapped
