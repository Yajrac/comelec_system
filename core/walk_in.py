from Applicants.application_types import APPLICATION_TYPE_LABELS
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render
from django.templatetags.static import static
from django.urls import reverse

from Applicants import views as applicant_views


SERVICES = {
    "new": (APPLICATION_TYPE_LABELS["NEW"], "new-registration", applicant_views.new_registration, applicant_views.registration_success, "applicant_id"),
    "transfer": (APPLICATION_TYPE_LABELS["TRANSFER"], "transfer-registration", applicant_views.transfer_registration, applicant_views.transfer_success, "request_id"),
    "reactivation": (APPLICATION_TYPE_LABELS["REACTIVATION"], "reactivation-registration", applicant_views.reactivate_registration, applicant_views.reactivation_success, "request_id"),
    "update": (APPLICATION_TYPE_LABELS["UPDATE"], "update-registration", applicant_views.update_registration, applicant_views.update_success, "request_id"),
    "reinstatement": (APPLICATION_TYPE_LABELS["REINSTATEMENT"], "reinstatement-registration", applicant_views.reinstate_registration, applicant_views.reinstatement_success, "request_id"),
}


@login_required
def walk_in(request, service=None, record_id=None):
    from .views import admin_superuser_required
    access = admin_superuser_required(request)
    if access:
        return access
    if service is None:
        from django.core.paginator import Paginator
        from django.db.models import Q
        from Applicants.models import Applicant, Barangay
        records = Applicant.objects.select_related("brgy").order_by("lastname", "firstname", "pk")
        search = request.GET.get("search", "").strip()
        barangay = request.GET.get("barangay", "")
        status = request.GET.get("status", "")
        if search:
            words = search.replace(",", " ").split()
            for word in words:
                records = records.filter(Q(firstname__icontains=word) | Q(lastname__icontains=word)
                    | Q(middlename__icontains=word) | Q(registration_reference__icontains=word))
        if barangay.isdigit():
            records = records.filter(brgy_id=barangay)
        if status in {"active", "inactive"}:
            records = records.filter(is_active=(status == "active"))
        page = Paginator(records, 10).get_page(request.GET.get("page"))
        params = request.GET.copy()
        params.pop("page", None)
        return render(request, "comelec/walk_in.html", {
            "records": page, "barangays": Barangay.objects.order_by("name"),
            "search": search, "selected_barangay": barangay, "selected_status": status,
            "query": params.urlencode(), "services": [
                {"key": key, "name": value[0]} for key, value in SERVICES.items() if key != "new"
            ],
        })
    if service not in SERVICES:
        raise Http404
    request.walk_in_base = "admin.html"
    _, _, form_view, success_view, id_key = SERVICES[service]
    response = success_view(request, **{id_key: record_id}) if record_id is not None else form_view(request)
    if response.status_code == 302:
        from django.urls import resolve
        match = resolve(response.url)
        success_id = match.kwargs.get(id_key)
        if success_id is not None:
            response["Location"] = reverse("admin-walk-in-success", args=[service, success_id])
        return response
    if response.get("Content-Type", "").startswith("text/html"):
        html = response.content.decode(response.charset)
        for key, value in SERVICES.items():
            html = html.replace(f'="{reverse(value[1])}"', f'="{reverse("admin-walk-in-form", args=[key])}"')
        html = html.replace(f'="{reverse("home")}"', f'="{reverse("admin-walk-in")}"')
        html = html.replace('</head>', f'<link rel="stylesheet" href="{static("css/application-forms.css")}"><link rel="stylesheet" href="{static("css/input-validation.css")}"></head>')
        html = html.replace('</body>', f'<script src="{static("js/input-validation.js")}" defer></script></body>')
        response.content = html
    return response
