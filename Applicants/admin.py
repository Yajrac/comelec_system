
from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Barangay,
    Applicant,
    ApplicantUpdateRequest,
    ApplicantTransferRequest,
    ApplicantReactivationRequest,
    ApplicantReinstatementRequest,
    ApplicantBiometric,
    ApplicantNotification,
    SignatureSession,
    FingerprintCaptureRequest,
)


# =========================================================
# COMMON ADMIN CONFIGURATION
# =========================================================

admin.site.site_header = "Pio Duran Online Registration Administration"
admin.site.site_title = "Registration Admin"
admin.site.index_title = "Applicant Registration Management"


# =========================================================
# BARANGAY ADMIN
# =========================================================

@admin.register(Barangay)
class BarangayAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
    )

    search_fields = (
        "name",
    )

    ordering = (
        "name",
    )


# =========================================================
# APPLICANT ADMIN
# =========================================================

@admin.register(Applicant)
class ApplicantAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "full_name",
        "email",
        "phone",
        "brgy",
        "application_type",
        "status",
        "verification_status",
        "is_active",
        "date_joined",
    )

    list_filter = (
        "application_type",
        "status",
        "verification_status",
        "is_active",
        "is_senior",
        "pwd_status",
        "citizenship_status",
        "sex",
        "brgy",
        "date_joined",
    )

    search_fields = (
        "firstname",
        "middlename",
        "lastname",
        "email",
        "phone",
    )

    readonly_fields = (
        "date_joined",
    )

    ordering = (
        "-date_joined",
    )

    list_per_page = 25

    @admin.display(description="Full Name", ordering="lastname")
    def full_name(self, obj):
        return (
            f"{obj.lastname}, {obj.firstname} "
            f"{obj.middlename or ''}"
        ).strip()


# =========================================================
# APPLICANT UPDATE REQUEST ADMIN
# =========================================================

@admin.register(ApplicantUpdateRequest)
class ApplicantUpdateRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "applicant",
        "requested_name",
        "email",
        "brgy",
        "status",
        "requested_at",
        "reviewed_at",
    )

    list_filter = (
        "status",
        "brgy",
        "requested_at",
        "reviewed_at",
    )

    search_fields = (
        "applicant__firstname",
        "applicant__middlename",
        "applicant__lastname",
        "firstname",
        "middlename",
        "lastname",
        "email",
    )

    readonly_fields = (
        "requested_at",
    )

    ordering = (
        "-requested_at",
    )

    list_per_page = 25

    @admin.display(description="Requested Name")
    def requested_name(self, obj):
        return (
            f"{obj.lastname}, {obj.firstname} "
            f"{obj.middlename or ''}"
        ).strip()


# =========================================================
# APPLICANT TRANSFER REQUEST ADMIN
# =========================================================

@admin.register(ApplicantTransferRequest)
class ApplicantTransferRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "applicant",
        "current_brgy",
        "new_brgy",
        "current_municipality",
        "new_municipality",
        "status",
        "requested_at",
        "reviewed_at",
    )

    list_filter = (
        "status",
        "current_brgy",
        "new_brgy",
        "requested_at",
    )

    search_fields = (
        "applicant__firstname",
        "applicant__middlename",
        "applicant__lastname",
        "applicant__email",
        "reason",
    )

    readonly_fields = (
        "requested_at",
    )

    ordering = (
        "-requested_at",
    )

    list_per_page = 25


# =========================================================
# APPLICANT REACTIVATION REQUEST ADMIN
# =========================================================

@admin.register(ApplicantReactivationRequest)
class ApplicantReactivationRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "applicant",
        "status",
        "requested_at",
        "reviewed_at",
    )

    list_filter = (
        "status",
        "requested_at",
    )

    search_fields = (
        "applicant__firstname",
        "applicant__middlename",
        "applicant__lastname",
        "applicant__email",
        "reason",
    )

    readonly_fields = (
        "requested_at",
    )

    ordering = (
        "-requested_at",
    )


# =========================================================
# APPLICANT REINSTATEMENT REQUEST ADMIN
# =========================================================

@admin.register(ApplicantReinstatementRequest)
class ApplicantReinstatementRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "applicant",
        "status",
        "requested_at",
        "reviewed_at",
    )

    list_filter = (
        "status",
        "requested_at",
    )

    search_fields = (
        "applicant__firstname",
        "applicant__middlename",
        "applicant__lastname",
        "applicant__email",
        "reason",
    )

    readonly_fields = (
        "requested_at",
    )

    ordering = (
        "-requested_at",
    )


# =========================================================
# APPLICANT BIOMETRIC ADMIN
# =========================================================

@admin.register(ApplicantBiometric)
class ApplicantBiometricAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "applicant",
        "left_fingerprint_status",
        "right_fingerprint_status",
        "signature_status",
        "completion_status",
        "captured_at",
        "updated_at",
    )

    list_filter = (
        "biometrics_completed",
        "completed",
        "captured_at",
        "updated_at",
    )

    search_fields = (
        "applicant__firstname",
        "applicant__middlename",
        "applicant__lastname",
        "applicant__email",
    )

    readonly_fields = (
        "left_fingerprint_preview",
        "right_fingerprint_preview",
        "signature_preview",
        "captured_at",
        "updated_at",
    )

    fieldsets = (
        (
            "Applicant Information",
            {
                "fields": (
                    "applicant",
                ),
            },
        ),
        (
            "Left Fingerprint",
            {
                "fields": (
                    "left_finger",
                    "left_fingerprint_preview",
                    "left_finger_template",
                ),
            },
        ),
        (
            "Right Fingerprint",
            {
                "fields": (
                    "right_finger",
                    "right_fingerprint_preview",
                    "right_finger_template",
                ),
            },
        ),
        (
            "Electronic Signature",
            {
                "fields": (
                    "applicant_signature",
                    "signature_preview",
                ),
            },
        ),
        (
            "Completion Status",
            {
                "fields": (
                    "biometrics_completed",
                    "completed",
                    "captured_at",
                    "updated_at",
                ),
            },
        ),
    )

    ordering = (
        "-updated_at",
    )

    list_per_page = 25

    @admin.display(description="Left Finger")
    def left_fingerprint_status(self, obj):
        if obj.left_finger:
            return format_html(
                '<span style="color: #15803d; font-weight: 600;">'
                'Saved</span>'
            )

        return format_html(
            '<span style="color: #dc2626; font-weight: 600;">'
            'Missing</span>'
        )

    @admin.display(description="Right Finger")
    def right_fingerprint_status(self, obj):
        if obj.right_finger:
            return format_html(
                '<span style="color: #15803d; font-weight: 600;">'
                'Saved</span>'
            )

        return format_html(
            '<span style="color: #dc2626; font-weight: 600;">'
            'Missing</span>'
        )

    @admin.display(description="Signature")
    def signature_status(self, obj):
        if obj.applicant_signature:
            return format_html(
                '<span style="color: #15803d; font-weight: 600;">'
                'Saved</span>'
            )

        return format_html(
            '<span style="color: #64748b;">Not provided</span>'
        )

    @admin.display(description="Biometrics Status")
    def completion_status(self, obj):
        # Completion is determined by the two fingerprint images.
        if obj.left_finger and obj.right_finger:
            return format_html(
                '<span style="background: #dcfce7; color: #166534; '
                'padding: 4px 9px; border-radius: 12px; '
                'font-weight: 600;">COMPLETE</span>'
            )

        return format_html(
            '<span style="background: #fef3c7; color: #92400e; '
            'padding: 4px 9px; border-radius: 12px; '
            'font-weight: 600;">PENDING</span>'
        )

    @admin.display(description="Left Fingerprint Preview")
    def left_fingerprint_preview(self, obj):
        if obj and obj.left_finger:
            try:
                return format_html(
                    '<a href="{}" target="_blank" rel="noopener">'
                    '<img src="{}" alt="Left fingerprint" '
                    'style="max-width: 280px; max-height: 280px; '
                    'object-fit: contain; border: 1px solid #ddd; '
                    'padding: 8px; background: white;" />'
                    '</a>',
                    obj.left_finger.url,
                    obj.left_finger.url,
                )
            except (ValueError, NotImplementedError):
                pass

        return "No left fingerprint image."

    @admin.display(description="Right Fingerprint Preview")
    def right_fingerprint_preview(self, obj):
        if obj and obj.right_finger:
            try:
                return format_html(
                    '<a href="{}" target="_blank" rel="noopener">'
                    '<img src="{}" alt="Right fingerprint" '
                    'style="max-width: 280px; max-height: 280px; '
                    'object-fit: contain; border: 1px solid #ddd; '
                    'padding: 8px; background: white;" />'
                    '</a>',
                    obj.right_finger.url,
                    obj.right_finger.url,
                )
            except (ValueError, NotImplementedError):
                pass

        return "No right fingerprint image."

    @admin.display(description="Signature Preview")
    def signature_preview(self, obj):
        if obj and obj.applicant_signature:
            try:
                return format_html(
                    '<a href="{}" target="_blank" rel="noopener">'
                    '<img src="{}" alt="Applicant signature" '
                    'style="max-width: 350px; max-height: 160px; '
                    'object-fit: contain; border: 1px solid #ddd; '
                    'padding: 8px; background: white;" />'
                    '</a>',
                    obj.applicant_signature.url,
                    obj.applicant_signature.url,
                )
            except (ValueError, NotImplementedError):
                pass

        return "No signature image."


# =========================================================
# APPLICANT NOTIFICATION ADMIN
# =========================================================

@admin.register(ApplicantNotification)
class ApplicantNotificationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "applicant",
        "title",
        "notification_type",
        "is_read",
        "created_at",
    )

    list_filter = (
        "notification_type",
        "is_read",
        "created_at",
    )

    search_fields = (
        "applicant__firstname",
        "applicant__middlename",
        "applicant__lastname",
        "applicant__email",
        "title",
        "message",
    )

    readonly_fields = (
        "created_at",
    )

    ordering = (
        "-created_at",
    )


# =========================================================
# SIGNATURE SESSION ADMIN
# =========================================================

@admin.register(SignatureSession)
class SignatureSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "session_id",
        "applicant",
        "officer",
        "status",
        "created_at",
        "completed_at",
        "cancelled_at",
    )

    list_filter = (
        "status",
        "created_at",
        "completed_at",
    )

    search_fields = (
        "session_id",
        "applicant__firstname",
        "applicant__middlename",
        "applicant__lastname",
        "applicant__email",
        "officer__username",
    )

    readonly_fields = (
        "session_id",
        "created_at",
    )

    ordering = (
        "-created_at",
    )

    list_per_page = 25


# =========================================================
# FINGERPRINT CAPTURE REQUEST ADMIN
# =========================================================

@admin.register(FingerprintCaptureRequest)
class FingerprintCaptureRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "applicant",
        "finger",
        "status",
        "message",
        "created_at",
        "updated_at",
    )

    list_filter = (
        "finger",
        "status",
        "created_at",
        "updated_at",
    )

    search_fields = (
        "applicant__firstname",
        "applicant__middlename",
        "applicant__lastname",
        "applicant__email",
        "message",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = (
        "-created_at",
    )

    list_per_page = 25
