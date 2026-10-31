from datetime import timedelta

from django.contrib.auth import authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.password_validation import get_default_password_validators
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import salted_hmac

from .models import AdminAccountSecurity, AdminLoginThrottle


def authenticate_admin(request, username, password):
    """Persistent account + IP throttling; never trust client-forwarded IP headers."""
    now = timezone.now()
    window = timedelta(minutes=15)
    keys = [(salted_hmac("admin-account", username.casefold()).hexdigest(), 5),
            (salted_hmac("admin-ip", request.META.get("REMOTE_ADDR", "unknown")).hexdigest(), 20)]
    with transaction.atomic():
        buckets = []
        for key, limit in sorted(keys):
            AdminLoginThrottle.objects.get_or_create(key=key, defaults={"window_started": now})
            bucket = AdminLoginThrottle.objects.select_for_update().get(key=key)
            if bucket.locked_until and bucket.locked_until > now:
                return None, "Too many unsuccessful attempts. Please try again in 15 minutes."
            if bucket.window_started + window <= now or bucket.locked_until:
                bucket.failures = 0
                bucket.window_started = now
                bucket.locked_until = None
            buckets.append((bucket, limit))
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_active and user.is_superuser:
            # Clear the account bucket only. Successful logins cannot reset IP abuse limits.
            AdminLoginThrottle.objects.filter(key=keys[0][0]).delete()
            return user, None
        locked = False
        for bucket, limit in buckets:
            bucket.failures += 1
            if bucket.failures >= limit:
                bucket.locked_until = now + window
                locked = True
            bucket.save()
        return None, ("Too many unsuccessful attempts. Please try again in 15 minutes."
                      if locked else "Invalid username or password.")


@login_required
def change_admin_password(request):
    if not request.user.is_superuser:
        return redirect("admin-login")
    form = PasswordChangeForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        if request.user.check_password(form.cleaned_data["new_password1"]):
            form.add_error("new_password1", "Choose a password different from your temporary or current password.")
        else:
            with transaction.atomic():
                user = form.save()
                AdminAccountSecurity.objects.update_or_create(user=user, defaults={"must_change_password": False})
            update_session_auth_hash(request, user)
            return redirect("dashboard")
    return render(request, "comelec/auth/change_password.html", {"form": form,
        "password_rules": [validator.get_help_text() for validator in get_default_password_validators()]})


@login_required
@require_POST
def password_requirements(request):
    if not request.user.is_superuser:
        return JsonResponse({"error": "Not authorized."}, status=403)
    password = request.POST.get("password", "")
    if len(password) > 4096:
        return JsonResponse({"error": "Password is too long."}, status=400)
    checks = []
    for validator in get_default_password_validators():
        try:
            validator.validate(password, request.user)
            checks.append(bool(password))
        except ValidationError:
            checks.append(False)
    response = JsonResponse({"checks": checks})
    response["Cache-Control"] = "no-store"
    return response


class RequireAdminPasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.user.is_superuser:
            allowed = {reverse("admin-change-password"), reverse("admin-logout"), reverse("admin-password-requirements")}
            if request.path not in allowed and AdminAccountSecurity.objects.filter(
                    user=request.user, must_change_password=True).exists():
                return redirect("admin-change-password")
        return self.get_response(request)
