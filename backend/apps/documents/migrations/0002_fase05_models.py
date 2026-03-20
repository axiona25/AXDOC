# FASE 05: Cartelle, estensione Document/DocumentVersion, allegati, permessi

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


def copy_name_to_title(apps, schema_editor):
    Document = apps.get_model("documents", "Document")
    for doc in Document.objects.all():
        doc.title = getattr(doc, "name", "") or ""
        doc.save(update_fields=["title"])


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("organizations", "0001_initial"),
        ("documents", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="MetadataStructure",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("schema", models.JSONField(default=dict, help_text="Schema campi metadati")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Struttura metadati",
                "verbose_name_plural": "Strutture metadati",
            },
        ),
        migrations.CreateModel(
            name="Folder",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_folders",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "parent",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="subfolders",
                        to="documents.folder",
                    ),
                ),
            ],
            options={
                "verbose_name": "Cartella",
                "verbose_name_plural": "Cartelle",
                "ordering": ["name"],
            },
        ),
        migrations.AddField(
            model_name="document",
            name="title",
            field=models.CharField(default="", max_length=500),
        ),
        migrations.RunPython(copy_name_to_title, migrations.RunPython.noop),
        migrations.RemoveField(model_name="document", name="name"),
        migrations.AddField(
            model_name="document",
            name="description",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="document",
            name="folder",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="documents",
                to="documents.folder",
            ),
        ),
        migrations.AddField(
            model_name="document",
            name="status",
            field=models.CharField(
                choices=[
                    ("DRAFT", "Bozza"),
                    ("IN_REVIEW", "In revisione"),
                    ("APPROVED", "Approvato"),
                    ("ARCHIVED", "Archiviato"),
                    ("REJECTED", "Rifiutato"),
                ],
                default="DRAFT",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="document",
            name="current_version",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name="document",
            name="is_deleted",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="document",
            name="metadata_structure",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="documents",
                to="documents.metadatastructure",
            ),
        ),
        migrations.AddField(
            model_name="document",
            name="metadata_values",
            field=models.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="document",
            name="locked_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="locked_documents",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="document",
            name="locked_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="documentversion",
            name="file_name",
            field=models.CharField(default="", max_length=500),
        ),
        migrations.AddField(
            model_name="documentversion",
            name="file_size",
            field=models.BigIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="documentversion",
            name="file_type",
            field=models.CharField(default="", max_length=255),
        ),
        migrations.AddField(
            model_name="documentversion",
            name="checksum",
            field=models.CharField(default="", max_length=64),
        ),
        migrations.AddField(
            model_name="documentversion",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="document_versions",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="documentversion",
            name="change_description",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="documentversion",
            name="is_current",
            field=models.BooleanField(default=True),
        ),
        migrations.CreateModel(
            name="DocumentAttachment",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("file", models.FileField(upload_to="attachments/%Y/%m/")),
                ("file_name", models.CharField(max_length=500)),
                ("file_size", models.BigIntegerField(default=0)),
                ("file_type", models.CharField(default="", max_length=255)),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                ("description", models.CharField(blank=True, max_length=500)),
                (
                    "document",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attachments",
                        to="documents.document",
                    ),
                ),
                (
                    "uploaded_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="document_attachments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Allegato",
                "verbose_name_plural": "Allegati",
                "ordering": ["-uploaded_at"],
            },
        ),
        migrations.CreateModel(
            name="DocumentPermission",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("can_read", models.BooleanField(default=True)),
                ("can_write", models.BooleanField(default=False)),
                ("can_delete", models.BooleanField(default=False)),
                (
                    "document",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="user_permissions",
                        to="documents.document",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="document_permissions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Permesso documento (utente)",
                "verbose_name_plural": "Permessi documento (utenti)",
                "unique_together": {("document", "user")},
            },
        ),
        migrations.CreateModel(
            name="DocumentOUPermission",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("can_read", models.BooleanField(default=True)),
                ("can_write", models.BooleanField(default=False)),
                (
                    "document",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ou_permissions",
                        to="documents.document",
                    ),
                ),
                (
                    "organizational_unit",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="document_permissions",
                        to="organizations.organizationalunit",
                    ),
                ),
            ],
            options={
                "verbose_name": "Permesso documento (UO)",
                "verbose_name_plural": "Permessi documento (UO)",
                "unique_together": {("document", "organizational_unit")},
            },
        ),
    ]
