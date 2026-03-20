# FASE 09: ProtocolCounter, estensione Protocol, allegati (RF-058..RF-063)

import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def migrate_direction_to_lowercase(apps, schema_editor):
    Protocol = apps.get_model("protocols", "Protocol")
    Protocol.objects.filter(direction="IN").update(direction="in")
    Protocol.objects.filter(direction="OUT").update(direction="out")


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("documents", "0003_alter_document_options_and_more"),
        ("organizations", "0001_initial"),
        ("protocols", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProtocolCounter",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("year", models.IntegerField()),
                ("last_number", models.IntegerField(default=0)),
                ("organizational_unit", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="protocol_counters", to="organizations.organizationalunit")),
            ],
            options={
                "verbose_name": "Contatore protocollo",
                "verbose_name_plural": "Contatori protocollo",
            },
        ),
        migrations.AlterModelOptions(
            name="protocol",
            options={"ordering": ["-registered_at", "-created_at"], "verbose_name": "Protocollo", "verbose_name_plural": "Protocolli"},
        ),
        migrations.AddField(
            model_name="protocol",
            name="number",
            field=models.IntegerField(blank=True, help_text="Progressivo anno/UO", null=True),
        ),
        migrations.AddField(
            model_name="protocol",
            name="year",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="protocol",
            name="protocol_id",
            field=models.CharField(blank=True, help_text="Es: 2024/IT/0042", max_length=100),
        ),
        migrations.AddField(
            model_name="protocol",
            name="document",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="protocols", to="documents.document"),
        ),
        migrations.AddField(
            model_name="protocol",
            name="subject",
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name="protocol",
            name="sender_receiver",
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name="protocol",
            name="registered_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="protocol",
            name="registered_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="registered_protocols", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="protocol",
            name="status",
            field=models.CharField(choices=[("active", "Attivo"), ("archived", "Archiviato")], default="active", max_length=20),
        ),
        migrations.AddField(
            model_name="protocol",
            name="notes",
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name="protocol",
            name="protocol_number",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AlterField(
            model_name="protocol",
            name="protocol_date",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(migrate_direction_to_lowercase, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="protocol",
            name="direction",
            field=models.CharField(choices=[("in", "In entrata"), ("out", "In uscita")], default="in", max_length=10),
        ),
        migrations.CreateModel(
            name="ProtocolAttachment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("added_at", models.DateTimeField(auto_now_add=True)),
                ("document", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="protocol_attachments", to="documents.document")),
                ("protocol", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="attachment_links", to="protocols.protocol")),
            ],
            options={
                "unique_together": {("protocol", "document")},
            },
        ),
        migrations.AddField(
            model_name="protocol",
            name="attachments",
            field=models.ManyToManyField(
                blank=True,
                related_name="attached_to_protocols",
                through="protocols.ProtocolAttachment",
                to="documents.document",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="protocol",
            unique_together={("organizational_unit", "year", "number")},
        ),
    ]
