# FASE 09: Fascicoli (RF-064..RF-069)

import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("documents", "0004_document_is_protocolled"),
        ("organizations", "0001_initial"),
        ("protocols", "0002_fase09_protocol_counter_and_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="Dossier",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("title", models.CharField(max_length=500)),
                ("identifier", models.CharField(max_length=100, unique=True)),
                ("description", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("open", "Aperto"), ("archived", "Archiviato"), ("closed", "Chiuso")], default="open", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("archived_at", models.DateTimeField(blank=True, null=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_dossiers", to=settings.AUTH_USER_MODEL)),
                ("responsible", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="responsible_dossiers", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Fascicolo",
                "verbose_name_plural": "Fascicoli",
                "ordering": ["-updated_at"],
            },
        ),
        migrations.CreateModel(
            name="DossierDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("added_at", models.DateTimeField(auto_now_add=True)),
                ("notes", models.CharField(blank=True, max_length=500)),
                ("added_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ("document", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="dossier_links", to="documents.document")),
                ("dossier", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="dossier_documents", to="dossiers.dossier")),
            ],
            options={
                "unique_together": {("dossier", "document")},
            },
        ),
        migrations.CreateModel(
            name="DossierProtocol",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("added_at", models.DateTimeField(auto_now_add=True)),
                ("added_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ("dossier", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="dossier_protocols", to="dossiers.dossier")),
                ("protocol", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="dossier_links", to="protocols.protocol")),
            ],
            options={
                "unique_together": {("dossier", "protocol")},
            },
        ),
        migrations.CreateModel(
            name="DossierPermission",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("can_read", models.BooleanField(default=True)),
                ("can_write", models.BooleanField(default=False)),
                ("dossier", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="user_permissions", to="dossiers.dossier")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="dossier_permissions", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "unique_together": {("dossier", "user")},
            },
        ),
        migrations.CreateModel(
            name="DossierOUPermission",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("can_read", models.BooleanField(default=True)),
                ("dossier", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ou_permissions", to="dossiers.dossier")),
                ("organizational_unit", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="dossier_permissions", to="organizations.organizationalunit")),
            ],
            options={
                "unique_together": {("dossier", "organizational_unit")},
            },
        ),
    ]
