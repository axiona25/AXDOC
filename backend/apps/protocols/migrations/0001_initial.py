# Generated manually for FASE 07 - Protocols AGID

import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("organizations", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Protocol",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("protocol_number", models.CharField(max_length=100)),
                ("protocol_date", models.DateTimeField()),
                ("direction", models.CharField(choices=[("IN", "In entrata"), ("OUT", "In uscita")], default="IN", max_length=10)),
                ("document_file", models.FileField(blank=True, help_text="Documento allegato da timbrare (PDF o convertibile in PDF)", null=True, upload_to="protocol_docs/")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_protocols", to=settings.AUTH_USER_MODEL)),
                ("organizational_unit", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="protocols", to="organizations.organizationalunit")),
            ],
            options={
                "verbose_name": "Protocollo",
                "verbose_name_plural": "Protocolli",
                "ordering": ["-protocol_date", "-created_at"],
            },
        ),
    ]
