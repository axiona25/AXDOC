# Generated for FASE 18 - applicable_to on MetadataStructure

from django.db import migrations, models


def default_applicable_to():
    return ["document"]


class Migration(migrations.Migration):

    dependencies = [
        ("metadata", "0002_signature_conservation_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="metadatastructure",
            name="applicable_to",
            field=models.JSONField(
                blank=True,
                default=default_applicable_to,
                help_text="Tipi entità: 'document', 'folder', 'dossier', 'email'. Default: ['document'].",
            ),
        ),
    ]
