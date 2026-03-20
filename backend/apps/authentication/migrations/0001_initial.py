# Generated manually for AXDOC FASE 01

import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="AuditLog",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "action",
                    models.CharField(
                        choices=[
                            ("LOGIN", "Login"),
                            ("LOGIN_FAILED", "Login Fallito"),
                            ("LOGOUT", "Logout"),
                            ("PASSWORD_RESET", "Reset Password"),
                            ("PASSWORD_CHANGED", "Password Cambiata"),
                            ("USER_CREATED", "Utente Creato"),
                            ("USER_UPDATED", "Utente Modificato"),
                            ("USER_INVITED", "Invito Inviato"),
                            ("INVITATION_ACCEPTED", "Invito Accettato"),
                            ("DOCUMENT_CREATED", "Documento Creato"),
                            ("DOCUMENT_UPLOADED", "Documento Caricato"),
                            ("DOCUMENT_DOWNLOADED", "Documento Scaricato"),
                            ("DOCUMENT_DELETED", "Documento Eliminato"),
                            ("DOCUMENT_SHARED", "Documento Condiviso"),
                            ("WORKFLOW_STARTED", "Workflow Avviato"),
                            ("WORKFLOW_APPROVED", "Documento Approvato"),
                            ("WORKFLOW_REJECTED", "Documento Rifiutato"),
                            ("PROTOCOL_CREATED", "Protocollo Creato"),
                            ("DOCUMENT_SIGNED", "Documento Firmato"),
                            ("DOCUMENT_CONSERVED", "Documento in Conservazione"),
                            ("DOCUMENT_ENCRYPTED", "Documento Cifrato"),
                        ],
                        max_length=50,
                    ),
                ),
                ("detail", models.JSONField(blank=True, default=dict)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.TextField(blank=True)),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="audit_logs",
                        to="users.user",
                    ),
                ),
            ],
            options={
                "ordering": ["-timestamp"],
                "verbose_name": "Audit Log",
            },
        ),
        migrations.CreateModel(
            name="PasswordResetToken",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("token", models.UUIDField(default=uuid.uuid4, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("used", models.BooleanField(default=False)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="password_reset_tokens",
                        to="users.user",
                    ),
                ),
            ],
            options={
                "verbose_name": "Token reset password",
            },
        ),
    ]
