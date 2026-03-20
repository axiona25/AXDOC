# Generated for FASE 18 - Dossier metadata (AGID)

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("metadata", "0003_applicable_to"),
        ("dossiers", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="dossier",
            name="metadata_structure",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="dossiers",
                to="metadata.metadatastructure",
            ),
        ),
        migrations.AddField(
            model_name="dossier",
            name="metadata_values",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
