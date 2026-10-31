from Applicants.application_types import APPLICATION_TYPE_LABELS
from django.shortcuts import render
from django.utils import timezone


def application_list_groups(applicants, updates, transfers, reactivations, reinstatements):
    groups = {}

    def add(person, barangay, application, kind):
        name = barangay.name if barangay else "Unassigned"
        groups.setdefault(name, []).append({
            "name": f"{person.lastname}, {person.firstname} {person.middlename}".strip().upper(),
            "address": ", ".join(filter(None, [name if barangay else "", person.municipality, person.province])),
            "type": kind,
            "status": application.get_status_display(),
        })

    # The applicant directory contains people, not one row per service request.
    # Year scoping is applied to the original registration queryset by the caller.
    seen = set()
    for item in applicants:
        if item.pk in seen:
            continue
        seen.add(item.pk)
        add(item, item.brgy, item, item.get_application_type_display())

    rows = sorted((row for group in groups.values() for row in group),
                  key=lambda row: (row["name"], row["type"], row["address"]))
    for index, row in enumerate(rows, 1):
        row["number"] = index
    return [{"barangay": "All Barangays", "rows": rows}] if rows else []


def render_application_list(request, applicants, updates, transfers, reactivations,
                            reinstatements, date_from, date_to, applicant_only=False, period_label=""):
    groups = application_list_groups(applicants, updates, transfers, reactivations, reinstatements)
    pages = []
    total = sum(len(group["rows"]) for group in groups)
    for group in groups:
        rows = group["rows"]
        for offset in range(0, len(rows), 18):
            pages.append({"barangay": group["barangay"], "rows": rows[offset:offset + 18]})
    if not pages:
        pages.append({"barangay": "All selected barangays", "rows": []})
    return render(request, "comelec/reports_print.html", {
        "period_label": period_label, "applicant_only": applicant_only, "pages": pages, "total": total, "generated_at": timezone.localtime(),
        "date_from": date_from, "date_to": date_to,
    })
