# FASE 10: Firma digitale e conservazione (RF-075..RF-080)

import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("documents", "0004_document_is_protocolled"),
        ("protocols", "0002_fase09_protocol_counter_and_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="SignatureRequest",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("format", models.CharField(choices=[("cades", "CAdES (.p7m)"), ("pades_invisible", "PAdES invisibile"), ("pades_graphic", "PAdES grafica")], max_length=20)),
                ("status", models.CharField(choices=[("pending_otp", "In attesa OTP"), ("pending_provider", "In elaborazione provider"), ("completed", "Completata"), ("failed", "Fallita"), ("expired", "Scaduta")], default="pending_otp", max_length=30)),
                ("provider", models.CharField(default="aruba", max_length=50)),
                ("provider_request_id", models.CharField(blank=True, max_length=255)),
                ("provider_response", models.JSONField(blank=True, default=dict)),
                ("otp_sent_at", models.DateTimeField(blank=True, null=True)),
                ("otp_expires_at", models.DateTimeField(blank=True, null=True)),
                ("otp_verified", models.BooleanField(default=False)),
                ("otp_attempts", models.IntegerField(default=0)),
                ("max_otp_resends", models.IntegerField(default=3)),
                ("otp_resend_count", models.IntegerField(default=0)),
                ("signed_file", models.FileField(blank=True, null=True, upload_to="signed/%Y/%m/")),
                ("signed_file_name", models.CharField(blank=True, max_length=500)),
                ("signed_at", models.DateTimeField(blank=True, null=True)),
                ("signature_reason", models.CharField(blank=True, max_length=500)),
                ("signature_location", models.CharField(blank=True, max_length=255)),
                ("graphic_signature_image", models.ImageField(blank=True, null=True, upload_to="sig_images/")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("error_message", models.TextField(blank=True)),
                ("document", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="signature_requests", to="documents.document")),
                ("document_version", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="signature_requests", to="documents.documentversion")),
                ("requested_by", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="requested_signatures", to=settings.AUTH_USER_MODEL)),
                ("signer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="signature_requests_as_signer", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Richiesta firma",
                "verbose_name_plural": "Richieste firma",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="ConservationRequest",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("provider", models.CharField(default="aruba", max_length=50)),
                ("provider_request_id", models.CharField(blank=True, max_length=255)),
                ("provider_package_id", models.CharField(blank=True, max_length=255)),
                ("provider_response", models.JSONField(blank=True, default=dict)),
                ("status", models.CharField(choices=[("draft", "Da inviare"), ("pending", "In attesa invio"), ("sent", "Inviato al provider"), ("in_progress", "In elaborazione"), ("completed", "Conservato"), ("failed", "Fallito"), ("rejected", "Rifiutato dal provider")], default="draft", max_length=20)),
                ("submitted_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("last_checked_at", models.DateTimeField(blank=True, null=True)),
                ("document_type", models.CharField(max_length=200)),
                ("document_date", models.DateField()),
                ("reference_number", models.CharField(blank=True, max_length=200)),
                ("conservation_class", models.CharField(default="1", max_length=10)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("error_message", models.TextField(blank=True)),
                ("certificate_url", models.CharField(blank=True, max_length=500)),
                ("document", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="conservation_requests", to="documents.document")),
                ("document_version", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="conservation_requests", to="documents.documentversion")),
                ("protocol", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="conservation_requests", to="protocols.protocol")),
                ("requested_by", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="conservation_requests", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Richiesta conservazione",
                "verbose_name_plural": "Richieste conservazione",
                "ordering": ["-created_at"],
            },
        ),
    ]
