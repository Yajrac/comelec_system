# Removes stray spaces from saved names (letter case is kept) so duplicate checks,
# search and printed lists are consistent with new records.

from django.db import migrations

FIELDS = ("lastname", "firstname", "middlename", "birthplace", "father", "mother")


def tidy_names(apps, schema_editor):
    for model_name in ("Applicant", "ApplicantUpdateRequest"):
        model = apps.get_model("Applicants", model_name)
        for record in model.objects.only("pk", *FIELDS).iterator():
            changes = {}
            for field in FIELDS:
                value = getattr(record, field)
                if isinstance(value, str):
                    cleaned = " ".join(value.split())
                    if cleaned != value:
                        changes[field] = cleaned
            if changes:
                model.objects.filter(pk=record.pk).update(**changes)


class Migration(migrations.Migration):

    dependencies = [
        ('Applicants', '0037_possible_duplicate_of'),
    ]

    operations = [
        migrations.RunPython(tidy_names, migrations.RunPython.noop),
    ]
