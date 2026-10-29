from django.urls import path
from . import views

urlpatterns = [
    path(
        "applicant/verify-new-registration/",
        views.verify_applicant_for_new_registration,
        name="verify-applicant-new-registration"
    ),
    path(
        "barangays/",
        views.barangay_list,
        name="barangay-list"
    ),
    path(
        "new-registration/",
        views.new_registration_api,
        name="new-registration-api"
    ),

    path(
        "applicants/find/",
        views.find_applicant,
        name="find-applicant"
    ),

    path(
        "applicant-update-requests/",
        views.create_applicant_update_request,
        name="create-applicant-update-request"
    ),
    path(
        "applicant-transfer-requests/",
        views.create_applicant_transfer_request,
        name="create-applicant-transfer-request"
    ),
    path(
    "applicant-reactivation-requests/",
    views.create_applicant_reactivation_request,
    name="create-applicant-reactivation-request"
),
path(
    "applicant-reinstatement-requests/",
    views.create_applicant_reinstatement_request,
    name="create-applicant-reinstatement-request"
),
]