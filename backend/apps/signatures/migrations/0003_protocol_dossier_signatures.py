# FASE 20: SignatureRequest per protocol/dossier, SignatureSequenceStep

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("protocols", "0002_fase09_protocol_counter_and_fields"),
        ("dossiers", "0002_dossier_metadata"),
        ("signatures", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="signaturerequest",
            name="target_type",
            field=models.CharField(
                choices=[("document", "Documento"), ("protocol", "Protocollo"), ("dossier", "Fascicolo")],
                default="document",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="signaturerequest",
            name="protocol",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="signature_requests",
                to="protocols.protocol",
            ),
        ),
        migrations.AddField(
            model_name="signaturerequest",
            name="dossier",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="signature_requests",
                to="dossiers.dossier",
            ),
        ),
        migrations.AddField(
            model_name="signaturerequest",
            name="sign_all_documents",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="signaturerequest",
            name="signed_document_ids",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="signaturerequest",
            name="signature_sequence",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="signaturerequest",
            name="current_signer_index",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="signaturerequest",
            name="require_sequential",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="signaturerequest",
            name="document",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="signature_requests",
                to="documents.document",
            ),
        ),
        migrations.AlterField(
            model_name="signaturerequest",
            name="document_version",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="signature_requests",
                to="documents.documentversion",
            ),
        ),
        migrations.AlterField(
            model_name="signaturerequest",
            name="signer",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="signature_requests_as_signer",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="signaturerequest",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending_otp", "In attesa OTP"),
                    ("pending_provider", "In elaborazione provider"),
                    ("completed", "Completata"),
                    ("failed", "Fallita"),
                    ("expired", "Scaduta"),
                    ("rejected", "Rifiutata"),
                ],
                default="pending_otp",
                max_length=30,
            ),
        ),
        migrations.CreateModel(
            name="SignatureSequenceStep",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("order", models.PositiveIntegerField()),
                ("role_required", models.CharField(choices=[("any", "Qualsiasi"), ("operator", "Operatore"), ("reviewer", "Revisore"), ("approver", "Approvatore"), ("admin", "Amministratore")], default="any", max_length=20)),
                ("status", models.CharField(choices=[("pending", "In attesa"), ("signed", "Firmato"), ("rejected", "Rifiutato"), ("skipped", "Saltato")], default="pending", max_length=20)),
                ("signed_at", models.DateTimeField(blank=True, null=True)),
                ("rejection_reason", models.TextField(blank=True)),
                ("certificate_info", models.JSONField(blank=True, default=dict)),
                ("signature_request", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sequence_steps", to="signatures.signaturerequest")),
                ("signer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="signature_sequence_steps", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["order"],
                "unique_together": {("signature_request", "order")},
                "verbose_name": "Step firma",
                "verbose_name_plural": "Step firma",
            },
        ),
    ]
