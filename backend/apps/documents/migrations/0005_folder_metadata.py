# Generated for FASE 18 - Folder metadata (AGID)

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("metadata", "0003_applicable_to"),
        ("documents", "0004_document_is_protocolled"),
    ]

    operations = [
        migrations.AddField(
            model_name="folder",
            name="metadata_structure",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="folders",
                to="metadata.metadatastructure",
            ),
        ),
        migrations.AddField(
            model_name="folder",
            name="metadata_values",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
