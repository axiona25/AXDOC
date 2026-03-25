# FASE 28 — GDPR consensi e campi utente

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0005_usergroup_organizational_unit_alter_user_groups"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="data_retention_days",
            field=models.IntegerField(
                default=3650,
                help_text="Giorni di conservazione dati personali (default 10 anni PA).",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="privacy_accepted_at",
            field=models.DateTimeField(
                blank=True,
                help_text="Ultima accettazione informativa privacy (GDPR).",
                null=True,
            ),
        ),
        migrations.CreateModel(
            name="ConsentRecord",
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
                (
                    "consent_type",
                    models.CharField(
                        choices=[
                            ("privacy_policy", "Informativa Privacy"),
                            ("data_processing", "Trattamento Dati"),
                            ("marketing", "Comunicazioni Marketing"),
                            ("analytics", "Analisi e Statistiche"),
                            ("third_party", "Condivisione Terze Parti"),
                        ],
                        max_length=50,
                    ),
                ),
                (
                    "version",
                    models.CharField(
                        help_text="Versione del documento accettato, es. '1.0'",
                        max_length=20,
                    ),
                ),
                ("granted", models.BooleanField(help_text="True = consenso dato, False = revocato")),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="consents",
                        to="users.user",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="consentrecord",
            index=models.Index(fields=["user", "consent_type"], name="usr_consent_usr_typ_idx"),
        ),
    ]
