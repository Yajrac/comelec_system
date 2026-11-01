import uuid

from django.conf import settings
from django.db import models
from .application_types import APPLICATION_TYPE_CHOICES
from .profile_details import SUFFIX_CHOICES, validate_photo, photo_upload_path


class ProfileDetails(models.Model):
    suffix = models.CharField(max_length=5, choices=SUFFIX_CHOICES, blank=True, default="")
    photo = models.ImageField(upload_to=photo_upload_path, blank=True, validators=[validate_photo])
    is_indigenous = models.BooleanField(default=False)
    is_illiterate = models.BooleanField(default=False)

    class Meta:
        abstract = True


class RequestedProfileDetails(ProfileDetails):
    profile_details_provided = models.BooleanField(default=False)

    class Meta:
        abstract = True

class Barangay(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


class MobileSubmissionReceipt(models.Model):
    client_reference = models.CharField(max_length=100, unique=True)
    endpoint = models.CharField(max_length=100)
    response = models.JSONField()
    status_code = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

def generate_registration_reference():
    return "PD-" + uuid.uuid4().hex.upper()


class Applicant(ProfileDetails):
    registration_reference = models.CharField(
        max_length=35, unique=True, default=generate_registration_reference,
        editable=False,
    )


    APPLICATION_CHOICES = APPLICATION_TYPE_CHOICES

    APPLICATION_STATUS = [
        ("APPROVED", "Approved"),
        ("DISAPPROVED", "Disapproved"),
        ("PENDING", "Pending"),
        ("REVIEW", "Review"),
    ]

    CIVIL_STATUS_CHOICES = [
        ("Single", "Single"),
        ("Married", "Married"),
        ("Widowed", "Widowed"),
        ("Separated", "Separated"),
    ]

    PWD_CHOICES = [
        ("NO", "Not PWD"),
        ("VISUAL", "Visual Disability"),
        ("HEARING", "Hearing Disability"),
        ("PHYSICAL", "Physical Disability"),
        ("INTELLECTUAL", "Intellectual Disability"),
        ("PSYCHOSOCIAL", "Psychosocial Disability"),
        ("MULTIPLE", "Multiple Disabilities"),
        ("OTHER", "Other"),
    ]

    VERIFICATION_STATUS = [
        ("UNVERIFIED", "Unverified"),
        ("BIOMETRICS_PENDING", "Biometrics Pending"),
        ("VERIFIED", "Verified"),
    ]

    CITIZENSHIP_CHOICES = [
        ("BY_BIRTH", "By Birth"),
        ("NATURALIZED", "Naturalized"),
    ]

    # Personal Information
    lastname = models.CharField(max_length=255)
    firstname = models.CharField(max_length=255)
    middlename = models.CharField(max_length=255)

    civil_status = models.CharField(
        max_length=20,
        choices=CIVIL_STATUS_CHOICES,
        default="Single",
    )

    age = models.IntegerField()
    sex = models.CharField(max_length=20)
    birthdate = models.DateField()
    birthplace = models.CharField(max_length=255)

    # Address
    brgy = models.ForeignKey(
        Barangay,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    province = models.CharField(
        max_length=255,
        default="Albay",
    )

    municipality = models.CharField(
        max_length=255,
        default="Pio Duran",
    )

    # Contact Information
    phone = models.CharField(max_length=11)
    email = models.EmailField(unique=True, blank=True, null=True)

    # Application Information
    application_type = models.CharField(
        max_length=20,
        choices=APPLICATION_CHOICES,
        default="NEW",
    )

    status = models.CharField(
        max_length=20,
        choices=APPLICATION_STATUS,
        default="PENDING",
    )

    verification_status = models.CharField(
        max_length=30,
        choices=VERIFICATION_STATUS,
        default="UNVERIFIED",
    )

    # Other Information
    pwd_status = models.CharField(
        max_length=20,
        choices=PWD_CHOICES,
        default="NO",
    )

    citizenship_status = models.CharField(
        max_length=20,
        choices=CITIZENSHIP_CHOICES,
        default="BY_BIRTH",
    )

    father = models.CharField(max_length=255, blank=True)
    mother = models.CharField(max_length=255, blank=True)

    # Uploaded ID or supporting document
    valid_id_document = models.FileField(
        upload_to="applicant_documents/",
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(default=True)
    is_senior = models.BooleanField(default=False)

    date_joined = models.DateField(auto_now_add=True)

    office_visit_date = models.DateField(
        null=True,
        blank=True,
    )

    office_visit_slot = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    @property
    def current_age(self):
        from django.utils import timezone
        today = timezone.localdate()
        return today.year - self.birthdate.year - ((today.month, today.day) < (self.birthdate.month, self.birthdate.day))

    def __str__(self):
        return f"{self.lastname}, {self.firstname} {self.middlename}"


class ApplicantUpdateRequest(RequestedProfileDetails):
    def get_application_type_display(self):
        return dict(APPLICATION_TYPE_CHOICES)["UPDATE"]


    REQUEST_STATUS = [
        ("PENDING", "Pending"),
        ("REVIEW", "Review"),
        ("APPROVED", "Approved"),
        ("DISAPPROVED", "Disapproved"),
    ]

    applicant = models.ForeignKey(
        "Applicant",
        on_delete=models.CASCADE,
        related_name="update_requests"
    )

    lastname = models.CharField(
        max_length=255
    )

    firstname = models.CharField(
        max_length=255
    )

    middlename = models.CharField(
        max_length=255
    )

    civil_status = models.CharField(
        max_length=20, choices=Applicant.CIVIL_STATUS_CHOICES, blank=True, default=""
    )

    age = models.IntegerField()

    sex = models.CharField(
        max_length=20
    )

    birthdate = models.DateField()

    birthplace = models.CharField(
        max_length=255
    )

    brgy = models.ForeignKey(
        "Barangay",
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )

    province = models.CharField(
        max_length=255,
        default="Albay"
    )

    municipality = models.CharField(
        max_length=255,
        default="Pio Duran"
    )

    phone = models.CharField(
        max_length=11
    )

    email = models.EmailField(blank=True)

    pwd_status = models.CharField(
        max_length=20
    )

    citizenship_status = models.CharField(
        max_length=20
    )

    father = models.CharField(
        max_length=255, blank=True
    )

    mother = models.CharField(
        max_length=255, blank=True
    )

    reason = models.TextField(
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=20,
        choices=REQUEST_STATUS,
        default="PENDING"
    )

    valid_id_document = models.FileField(
        upload_to="applicant_update_documents/",
        null=True,
        blank=True,
    )

    requested_at = models.DateTimeField(
        auto_now_add=True
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    def __str__(self):
        return (
            f"{self.applicant} - "
            f"Update Request #{self.id}"
        )


class ApplicantTransferRequest(RequestedProfileDetails):
    def get_application_type_display(self):
        return dict(APPLICATION_TYPE_CHOICES)["TRANSFER"]


    REQUEST_STATUS = [
        ("PENDING", "Pending"),
        ("REVIEW", "Review"),
        ("APPROVED", "Approved"),
        ("DISAPPROVED", "Disapproved"),
    ]

    applicant = models.ForeignKey(
        "Applicant",
        on_delete=models.CASCADE,
        related_name="transfer_requests"
    )

    current_brgy = models.ForeignKey(
        "Barangay",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="current_transfer_requests"
    )

    new_brgy = models.ForeignKey(
        "Barangay",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="new_transfer_requests"
    )

    current_municipality = models.CharField(
        max_length=255,
        default="Pio Duran"
    )

    current_province = models.CharField(
        max_length=255,
        default="Albay"
    )

    new_municipality = models.CharField(
        max_length=255,
        default="Pio Duran"
    )

    new_province = models.CharField(
        max_length=255,
        default="Albay"
    )

    reason = models.TextField(
        blank=True,
        null=True
    )

    valid_id_document = models.FileField(
        upload_to="applicant_transfer_documents/",
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=REQUEST_STATUS,
        default="PENDING"
    )

    requested_at = models.DateTimeField(
        auto_now_add=True
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    def __str__(self):
        return (
            f"{self.applicant} - "
            f"Transfer Request #{self.id}"
        )



class ApplicantReactivationRequest(RequestedProfileDetails):
    def get_application_type_display(self):
        return dict(APPLICATION_TYPE_CHOICES)["REACTIVATION"]


    REQUEST_STATUS = [
        ("PENDING", "Pending"),
        ("REVIEW", "Review"),
        ("APPROVED", "Approved"),
        ("DISAPPROVED", "Disapproved"),
    ]

    applicant = models.ForeignKey(
        "Applicant",
        on_delete=models.CASCADE,
        related_name="reactivation_requests",
    )

    # Uploaded valid ID
    valid_id_document = models.FileField(
        upload_to="applicant_reactivation_documents/",
        null=True,
        blank=True,
    )

    reason = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=REQUEST_STATUS,
        default="PENDING",
    )

    requested_at = models.DateTimeField(
        auto_now_add=True,
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    def __str__(self):
        return (
            f"{self.applicant} - "
            f"Reactivation Request #{self.id}"
        )


class ApplicantReinstatementRequest(RequestedProfileDetails):
    def get_application_type_display(self):
        return dict(APPLICATION_TYPE_CHOICES)["REINSTATEMENT"]

    REQUEST_STATUS = [
        ("PENDING", "Pending"),
        ("REVIEW", "Review"),
        ("APPROVED", "Approved"),
        ("DISAPPROVED", "Disapproved"),
    ]

    applicant = models.ForeignKey(
        "Applicant",
        on_delete=models.CASCADE,
        related_name="reinstatement_requests",
    )

    # Supporting identity document for this reinstatement request
    valid_id_document = models.FileField(
        upload_to="applicant_reinstatement_documents/",
        null=True,
        blank=True,
    )

    reason = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=REQUEST_STATUS,
        default="PENDING",
    )

    requested_at = models.DateTimeField(auto_now_add=True)

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    def __str__(self):
        return (
            f"{self.applicant} - "
            f"Reinstatement Request #{self.id}"
        )

class ApplicantBiometric(models.Model):

    applicant = models.OneToOneField(
        Applicant,
        on_delete=models.CASCADE,
        related_name="biometric"
    )

    # =========================================================
    # LEFT FINGER
    # =========================================================

    left_finger = models.FileField(
        upload_to="biometrics/left/",
        null=True,
        blank=True
    )

    left_finger_template = models.TextField(
        null=True,
        blank=True
    )

    # =========================================================
    # RIGHT FINGER
    # =========================================================

    right_finger = models.FileField(
        upload_to="biometrics/right/",
        null=True,
        blank=True
    )

    right_finger_template = models.TextField(
        null=True,
        blank=True
    )

    # =========================================================
    # ELECTRONIC SIGNATURES
    # =========================================================

    applicant_signature = models.FileField(
        upload_to="biometrics/signatures/",
        null=True,
        blank=True
    )

    applicant_signature_2 = models.FileField(upload_to="biometrics/signatures/", null=True, blank=True)
    applicant_signature_3 = models.FileField(upload_to="biometrics/signatures/", null=True, blank=True)

    # =========================================================
    # CAPTURE STATUS
    # =========================================================

    biometrics_completed = models.BooleanField(
        default=False
    )

    completed = models.BooleanField(
        default=False
    )

    captured_at = models.DateTimeField(
        null=True,
        blank=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"Biometrics - {self.applicant}"


class ApplicantNotification(models.Model):

    NOTIFICATION_TYPE = [
        ("APPROVED", "Application Approved"),
        ("BIOMETRICS", "Biometrics Required"),
        ("VERIFIED", "Registration Verified"),
        ("GENERAL", "General"),
    ]

    applicant = models.ForeignKey(
        Applicant,
        on_delete=models.CASCADE,
        related_name="notifications"
    )

    notification_type = models.CharField(
        max_length=30,
        choices=NOTIFICATION_TYPE,
        default="GENERAL"
    )

    title = models.CharField(
        max_length=255
    )

    message = models.TextField()

    is_read = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.title} - {self.applicant}"

class SignatureSession(models.Model):

    STATUS_WAITING = "WAITING"
    STATUS_COMPLETED = "COMPLETED"
    STATUS_CANCELLED = "CANCELLED"
    STATUS_EXPIRED = "EXPIRED"

    STATUS_CHOICES = [
        (STATUS_WAITING, "Waiting"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_EXPIRED, "Expired"),
    ]

    signature_slot = models.PositiveSmallIntegerField(default=1, choices=[(1, "Signature 1"), (2, "Signature 2"), (3, "Signature 3")])

    session_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False
    )

    applicant = models.ForeignKey(
        Applicant,
        on_delete=models.CASCADE,
        related_name="signature_sessions"
    )

    officer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="signature_sessions"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_WAITING
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    cancelled_at = models.DateTimeField(
        null=True,
        blank=True
    )

    def __str__(self):
        return (
            f"Signature Session - "
            f"{self.applicant} - "
            f"{self.status}"
        )



class FingerprintCaptureRequest(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("capturing", "Capturing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    applicant = models.ForeignKey(
        Applicant,
        on_delete=models.CASCADE,
        related_name="fingerprint_capture_requests",
    )

    finger = models.CharField(
        max_length=10,
        choices=[
            ("left", "Left"),
            ("right", "Right"),
        ],
    )

    status = models.CharField(
        max_length=12,
        choices=STATUS_CHOICES,
        default="pending",
    )

    message = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return (
            f"Applicant {self.applicant_id} - "
            f"{self.finger} - {self.status}"
        )


class AcknowledgmentReceipt(models.Model):
    applicant = models.OneToOneField(Applicant, on_delete=models.PROTECT, related_name="acknowledgment_receipt")
    application_number = models.CharField(max_length=12, unique=True)
    details = models.JSONField(default=dict)
    issued_at = models.DateTimeField(auto_now_add=True)
    issued_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
