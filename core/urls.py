from django.urls import path
from . import views
from .receipts import acknowledgment_receipt
from .signatures import signature_device
from .walk_in import walk_in
from .admin_security import change_admin_password, password_requirements

urlpatterns = [
    path("signature/<uuid:session_id>/", signature_device, name="signature-device"),
    path("admin-applicants/<int:applicant_id>/receipt/", acknowledgment_receipt, name="acknowledgment-receipt"),
    path("password-requirements/", password_requirements, name="admin-password-requirements"),
    path("change-password/", change_admin_password, name="admin-change-password"),
    path("walk-in/", walk_in, name="admin-walk-in"),
    path("walk-in/<str:service>/", walk_in, name="admin-walk-in-form"),
    path("walk-in/<str:service>/success/<int:record_id>/", walk_in, name="admin-walk-in-success"),
    path("api/keep-alive/", views.keep_alive, name="keep_alive"),
    path(
        "admin/",
        views.admin_login,
        name="admin-login"
    ),

    path(
        "dashboard/",
        views.admin_dashboard,
        name="dashboard"
    ),

    path(
        "admin-logout/",
        views.admin_logout,
        name="admin-logout"
    ),
    path('add-barangay/', views.add_brgy, name="add_brgy"),
    path('brgy-list/', views.brgy_list, name="brgy_list"),
    path('delete-brgy/<int:pk>/', views.delete_brgy, name="delete-brgy"),

    path(
        "admin-applications/",
        views.admin_applications,
        name="admin-applications"
    ),

    path(
        "admin-applications/new/<int:application_id>/",
        views.admin_application_new_detail,
        name="admin-application-new-detail"
    ),

    path(
        "admin-applications/update/<int:application_id>/",
        views.admin_application_update_detail,
        name="admin-application-update-detail"
    ),

    path(
        "admin-applications/transfer/<int:application_id>/",
        views.admin_application_transfer_detail,
        name="admin-application-transfer-detail"
    ),

    path(
        "admin-applications/reactivation/<int:application_id>/",
        views.admin_application_reactivation_detail,
        name="admin-application-reactivation-detail"
    ),

    path(
        "admin-applications/reinstatement/<int:application_id>/",
        views.admin_application_reinstatement_detail,
        name="admin-application-reinstatement-detail"
    ),
    path(
        "admin-applications/<str:application_type>/<int:application_id>/<str:action>/",
        views.admin_application_action,
        name="admin-application-action"
    ),
    path(
        "admin-applicants/<int:applicant_id>/biometric/",
        views.admin_applicant_biometric,
        name="admin-applicant-biometric"
    ),
    path(
        "admin-applicants/<int:applicant_id>/print-slip/",
        views.print_slip_account,
        name="print-slip-account"
    ),
    path(
        "admin-applicants/",
        views.admin_applicants,
        name="admin-applicants"
    ),

    path(
        "admin-applicants/<int:applicant_id>/",
        views.admin_applicant_detail,
        name="admin-applicant-detail"
    ),

    path(
        "admin-applicants/<int:applicant_id>/suspend/",
        views.admin_suspend_applicant,
        name="admin-suspend-applicant"
    ),
    path(
        "admin-reports/",
        views.admin_reports,
        name="admin-reports"
    ),

    path(
        "admin-reports/export/",
        views.admin_reports_export,
        name="admin-reports-export"
    ),

    path(
        "applications/<int:id>/delete/",
        views.delete_application,
        name="delete-application"
    ),

    path(
        "barangays/<int:pk>/applicants/",
        views.barangay_applicants,
        name="barangay_applicants"
    ),
    path(
        "api/applicants/<int:applicant_id>/fingerprint/",
        views.save_fingerprint,
        name="save-fingerprint",
    ),
    path(
        "admin/applications/<int:applicant_id>/biometric/capture/",
        views.admin_capture_fingerprint,
        name="admin-capture-fingerprint"
    ),
    # =========================================================
    # START SIGNATURE SESSION
    # =========================================================

    path(
        "admin/applicants/<int:applicant_id>/signature/start/",
        views.start_signature_session,
        name="start-signature-session",
    ),

    # =========================================================
    # ANDROID: WAITING SESSION
    # =========================================================

    path(
        "api/signature/waiting/",
        views.get_waiting_signature_session,
        name="get-waiting-signature-session",
    ),

    # =========================================================
    # ANDROID: COMPLETE SIGNATURE
    # =========================================================

    path(
        "api/signature/complete/",
        views.complete_signature_session,
        name="complete-signature-session",
    ),

    # =========================================================
    # COMELeC: SESSION STATUS
    # =========================================================

    path(
        "admin/signature/session/<uuid:session_id>/status/",
        views.signature_session_status,
        name="signature-session-status",
    ),
    path(
    "admin/signature/session/<uuid:session_id>/cancel/",
    views.cancel_signature_session,
    name="cancel-signature-session",
),

path(
    "api/device/applicants/<int:applicant_id>/fingerprint/",
    views.fingerprint_device_upload,
    name="fingerprint-device-upload",
),

path(
    "admin/applications/<int:applicant_id>/fingerprint/start/",
    views.start_fingerprint_capture,
    name="start-fingerprint-capture",
),
path(
    "api/device/fingerprint/next/",
    views.fingerprint_device_next,
    name="fingerprint-device-next",
),
path(
    "api/device/fingerprint/complete/",
    views.fingerprint_device_complete,
    name="fingerprint-device-complete",
),
path(
    "admin/fingerprint-capture/<int:request_id>/status/",
    views.fingerprint_capture_status,
    name="fingerprint-capture-status",
),
path(
    "api/applicants/<int:applicant_id>/fingerprint/",
    views.save_fingerprint,
    name="save-fingerprint",
),

]
