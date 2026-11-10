from django.db import models
from django.conf import settings

class AdminAccountSecurity(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    must_change_password = models.BooleanField(default=False)


class AdminLoginThrottle(models.Model):
    key = models.CharField(max_length=64, primary_key=True)
    failures = models.PositiveIntegerField(default=0)
    window_started = models.DateTimeField()
    locked_until = models.DateTimeField(null=True, blank=True)


class ReceiptSettings(models.Model):
    officer_name = models.CharField(max_length=100, blank=True)
