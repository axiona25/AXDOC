# Generated for FASE 19 - Document visibility and owner (I miei File)

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0005_folder_metadata"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="visibility",
            field=models.CharField(
                choices=[
                    ("personal", "Personale"),
                    ("office", "Ufficio"),
                    ("shared", "Condiviso"),
                ],
                default="personal",
                help_text="personal: solo autore; office: tutti i membri UO; shared: condivisione esplicita.",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="document",
            name="owner",
            field=models.ForeignKey(
                blank=True,
                help_text="Proprietario (impostato a created_by alla creazione).",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="owned_documents",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
