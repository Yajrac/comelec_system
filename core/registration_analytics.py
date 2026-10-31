from calendar import month_name
from collections import Counter

from django.db.models import Count
from django.db.models.functions import ExtractMonth, ExtractYear
from django.utils import timezone

from Applicants.models import (Applicant, ApplicantUpdateRequest, ApplicantTransferRequest,
                               ApplicantReactivationRequest, ApplicantReinstatementRequest)


TREND_COLUMNS = [("period", "Period"), ("new", "New"), ("update", "Update"),
                 ("transfer", "Transfer"), ("reactivation", "Reactivation"),
                 ("reinstatement", "Reinstatement"), ("total", "Total"), ("change", "Change")]
DEMOGRAPHIC_COLUMNS = [("dimension", "Category"), ("name", "Group"),
                       ("total", "Applicants"), ("share", "Share")]


def registration_analytics(year=None):
    """Trends count submissions; demographics count each original applicant once."""
    sources = [(Applicant, "date_joined", "new"), (ApplicantUpdateRequest, "requested_at", "update"),
               (ApplicantTransferRequest, "requested_at", "transfer"),
               (ApplicantReactivationRequest, "requested_at", "reactivation"),
               (ApplicantReinstatementRequest, "requested_at", "reinstatement")]
    counts = {}
    periods = set(range(1, 13)) if year else set()
    for model, field, key in sources:
        queryset = model.objects.all()
        if year:
            queryset = queryset.filter(**{field + "__year": year})
        expression = ExtractMonth(field) if year else ExtractYear(field)
        result = queryset.order_by().annotate(period=expression).values("period").annotate(total=Count("pk"))
        counts[key] = {row["period"]: row["total"] for row in result if row["period"] is not None}
        periods.update(counts[key])
    if not periods:
        periods = {timezone.localdate().year}
    elif not year:
        periods = set(range(min(periods), max(periods) + 1))
    trends = []
    previous = None
    for period in sorted(periods):
        row = {"period": f"{month_name[period]} {year}" if year else str(period)}
        row.update({key: counts[key].get(period, 0) for _, _, key in sources})
        row["total"] = sum(row[key] for _, _, key in sources)
        row["change"] = "—" if previous is None else f'{row["total"] - previous:+d}'
        previous = row["total"]
        trends.append(row)

    applicants = Applicant.objects.all()
    if year:
        applicants = applicants.filter(date_joined__year=year)
    today = timezone.localdate()
    age_labels = ["Under 15", "15–17", "18–30", "31–45", "46–59", "60+"]
    ages, sexes, pwd = Counter(), Counter(), Counter()
    total = 0
    for record in applicants.values("birthdate", "sex", "pwd_status"):
        total += 1
        born = record["birthdate"]
        age = today.year - born.year - ((today.month, today.day) < (born.month, born.day)) if born else -1
        group = ("Unknown" if age < 0 or age > 150 else "Under 15" if age < 15 else "15–17" if age < 18 else
                 "18–30" if age <= 30 else "31–45" if age <= 45 else "46–59" if age <= 59 else "60+")
        ages[group] += 1
        sex = (record["sex"] or "").strip().upper()
        sexes[{"MALE": "Male", "FEMALE": "Female"}.get(sex, "Unknown")] += 1
        status = (record["pwd_status"] or "").strip().upper()
        pwd["Not PWD" if status == "NO" else "PWD" if status in dict(Applicant.PWD_CHOICES) or status == "YES" else "Unknown"] += 1
    demographics = []
    charts = {}
    for dimension, key, labels, counter in [
            ("Age group", "age", age_labels, ages),
            ("Sex", "sex", ["Male", "Female", "Unknown"], sexes),
            ("PWD status", "pwd", ["PWD", "Not PWD", "Unknown"], pwd)]:
        charts[key] = {"labels": labels, "values": [counter[label] for label in labels]}
        demographics.extend({"dimension": dimension, "name": label, "total": counter[label],
                             "share": f"{counter[label] * 100 / total:.1f}%" if total else "0.0%"} for label in labels)
    return {"trends": trends, "demographics": demographics, "demographic_total": total,
            "as_of": today, "charts": {**charts, "trends": {
                "labels": [row["period"] for row in trends], "values": [row["total"] for row in trends]}},
            "year": year}
