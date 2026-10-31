from getpass import getpass
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from core.models import AdminAccountSecurity


class Command(BaseCommand):
    help = "Create or reset a client admin with a temporary password requiring replacement at login."

    def add_arguments(self, parser):
        parser.add_argument("username")

    def handle(self, *args, **options):
        username = options["username"].strip()
        User = get_user_model()
        user = User.objects.filter(username=username).first()
        if not username or len(username) > 150:
            raise CommandError("Enter a valid username (maximum 150 characters).")
        if user and not user.is_superuser:
            raise CommandError("Existing account is not an admin; it was not changed.")
        candidate = user or User(username=username, is_staff=True, is_superuser=True, is_active=True)
        password = getpass("Temporary password: ")
        if password != getpass("Confirm temporary password: "):
            raise CommandError("Passwords do not match.")
        try:
            validate_password(password, candidate)
        except ValidationError as error:
            raise CommandError("; ".join(error.messages))
        with transaction.atomic():
            candidate.set_password(password)
            candidate.save()
            AdminAccountSecurity.objects.update_or_create(user=candidate, defaults={"must_change_password": True})
        self.stdout.write(self.style.SUCCESS("Client admin prepared. Password replacement is required before workspace access."))
