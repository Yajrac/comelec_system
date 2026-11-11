"""Read saved application requests without modifying the applicant profile."""
from datetime import datetime, time
from django.urls import reverse
from django.utils import timezone

REQUEST_HISTORY = (
    ('UPDATE', 'Correction / Update', 'update_requests', 'admin-application-update-detail'),
    ('TRANSFER', 'Transfer', 'transfer_requests', 'admin-application-transfer-detail'),
    ('REACTIVATION', 'Reactivation', 'reactivation_requests', 'admin-application-reactivation-detail'),
    ('REINSTATEMENT', 'Reinstatement', 'reinstatement_requests', 'admin-application-reinstatement-detail'),
)

TYPE_LABELS = {'NEW': 'New Registration', **{code: label for code, label, _, _ in REQUEST_HISTORY}}


def round_label(application_type, request_id):
    """Short name of a verification round, e.g. "Transfer #3"."""
    label = TYPE_LABELS.get(application_type, application_type)
    return f'{label} #{request_id}' if request_id else label


def application_history(applicant):
    initial_date = timezone.make_aware(datetime.combine(applicant.date_joined, time.min))
    rows = [{
        'type': 'NEW', 'key': 'NEW', 'label': 'New Registration',
        'reference': applicant.registration_reference,
        'submitted_at': initial_date, 'reviewed_at': None,
        'status': applicant.status, 'status_label': applicant.get_status_display(),
        'url': reverse('admin-application-new-detail', args=[applicant.pk]),
    }]
    for code, label, relation, view in REQUEST_HISTORY:
        for record in getattr(applicant, relation).all():
            rows.append({
                'type': code, 'key': f'{code}-{record.pk}', 'label': label, 'reference': f'{code}-{record.pk}',
                'submitted_at': record.requested_at, 'reviewed_at': record.reviewed_at,
                'status': record.status, 'status_label': record.get_status_display(),
                'url': reverse(view, args=[record.pk]),
            })
    return sorted(rows, key=lambda row: row['submitted_at'], reverse=True)
