# FASE 28 — SecurityIncident

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SecurityIncident",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField()),
                (
                    "severity",
                    models.CharField(
                        choices=[
                            ("low", "Basso"),
                            ("medium", "Medio"),
                            ("high", "Alto"),
                            ("critical", "Critico"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("open", "Aperto"),
                            ("investigating", "In indagine"),
                            ("mitigated", "Mitigato"),
                            ("resolved", "Risolto"),
                            ("closed", "Chiuso"),
                        ],
                        default="open",
                        max_length=20,
                    ),
                ),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("unauthorized_access", "Accesso non autorizzato"),
                            ("data_breach", "Violazione dati"),
                            ("malware", "Malware"),
                            ("phishing", "Phishing"),
                            ("dos", "Denial of Service"),
                            ("misconfiguration", "Errata configurazione"),
                            ("other", "Altro"),
                        ],
                        max_length=50,
                    ),
                ),
                ("affected_systems", models.TextField(blank=True, default="")),
                ("affected_users_count", models.IntegerField(default=0)),
                ("data_compromised", models.BooleanField(default=False)),
                ("containment_actions", models.TextField(blank=True, default="")),
                ("remediation_actions", models.TextField(blank=True, default="")),
                ("reported_to_authority", models.BooleanField(default=False)),
                ("authority_report_date", models.DateTimeField(blank=True, null=True)),
                ("authority_reference", models.CharField(blank=True, default="", max_length=100)),
                (
                    "detected_at",
                    models.DateTimeField(help_text="Quando è stato rilevato l'incidente"),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                (
                    "assigned_to",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="assigned_incidents",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "reported_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reported_incidents",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-detected_at"],
            },
        ),
    ]
