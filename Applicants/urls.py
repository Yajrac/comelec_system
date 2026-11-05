from django.urls import path

from . import views
from . import offline


urlpatterns = [
    path('offline/', offline.saved_applications, name='applicant-offline'),
    path('web-offline-sw.js', offline.service_worker, name='web-offline-worker'),
    path('offline/connection/', offline.connection_status, name='web-connection-status'),
    path('offline/shell/home/', offline.offline_shell, {'page': 'home'}, name='offline-home-shell'),
    path('offline/shell/registration/', offline.offline_shell, {'page': 'registration'}, name='offline-registration-shell'),
    path('offline/shell/saved/', offline.offline_shell, {'page': 'saved'}, name='offline-saved-shell'),

    path(
        "",
        views.home,
        name="home"
    ),

    path(
        "verify-new-registration/",
        views.verify_new_registration,
        name="verify-new-registration"
    ),

    path(
        "new-registration/",
        views.new_registration,
        name="new-registration"
    ),

    path(
        "registration-success/<int:applicant_id>/",
        views.registration_success,
        name="registration-success"
    ),
    path(
        "update-registration/",
        views.update_registration,
        name="update-registration"
    ),

    path(
        "update-success/<int:request_id>/",
        views.update_success,
        name="update-success"
    ),
    path(
        "transfer-registration/",
        views.transfer_registration,
        name="transfer-registration"
    ),

    path(
        "transfer-success/<int:request_id>/",
        views.transfer_success,
        name="transfer-success"
    ),
    path(
        "reactivation-registration/",
        views.reactivate_registration,
        name="reactivation-registration"
    ),

    path(
        "reactivation-success/<int:request_id>/",
        views.reactivation_success,
        name="reactivation-success"
    ),
    path(
        "reinstatement-registration/",
        views.reinstate_registration,
        name="reinstatement-registration"
    ),

    path(
        "reinstatement-success/<int:request_id>/",
        views.reinstatement_success,
        name="reinstatement-success"
    ),
]
