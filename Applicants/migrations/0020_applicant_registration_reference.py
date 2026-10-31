import uuid
from django.db import migrations, models
import Applicants.models


def populate_references(apps, schema_editor):
    Applicant = apps.get_model("Applicants", "Applicant")
    records = Applicant.objects.using(schema_editor.connection.alias)
    for applicant in records.filter(registration_reference__isnull=True).iterator():
        applicant.registration_reference = "PD-" + uuid.uuid4().hex.upper()
        applicant.save(using=schema_editor.connection.alias, update_fields=["registration_reference"])


class Migration(migrations.Migration):
    dependencies = [("Applicants", "0019_applicantreinstatementrequest_valid_id_document")]
    operations = [
        migrations.AddField(model_name="applicant", name="registration_reference", field=models.CharField(max_length=35, null=True, editable=False)),
        migrations.RunPython(populate_references, migrations.RunPython.noop),
        migrations.AlterField(model_name="applicant", name="registration_reference", field=models.CharField(max_length=35, unique=True, default=Applicants.models.generate_registration_reference, editable=False)),
    ]
