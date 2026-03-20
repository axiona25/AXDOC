# FASE 11: Condivisione documenti e protocolli

import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def gen_token():
    return uuid.uuid4().hex


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("documents", "0004_document_is_protocolled"),
        ("protocols", "0002_fase09_protocol_counter_and_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="ShareLink",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("token", models.CharField(db_index=True, default=gen_token, max_length=64, unique=True)),
                ("target_type", models.CharField(choices=[("document", "Documento"), ("protocol", "Protocollo")], max_length=20)),
                ("recipient_type", models.CharField(choices=[("internal", "Utente interno"), ("external", "Utente esterno")], max_length=20)),
                ("recipient_email", models.EmailField(blank=True, max_length=254)),
                ("recipient_name", models.CharField(blank=True, max_length=255)),
                ("can_download", models.BooleanField(default=True)),
                ("password_protected", models.BooleanField(default=False)),
                ("access_password", models.CharField(blank=True, max_length=128)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("max_accesses", models.IntegerField(blank=True, null=True)),
                ("access_count", models.IntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("last_accessed_at", models.DateTimeField(blank=True, null=True)),
                ("document", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="share_links", to="documents.document")),
                ("protocol", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="share_links", to="protocols.protocol")),
                ("recipient_user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="received_shares", to=settings.AUTH_USER_MODEL)),
                ("shared_by", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="created_share_links", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Link condivisione",
                "verbose_name_plural": "Link condivisione",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="ShareAccessLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("accessed_at", models.DateTimeField(auto_now_add=True)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.TextField(blank=True)),
                ("action", models.CharField(choices=[("view", "Visualizzazione"), ("download", "Download")], max_length=20)),
                ("share_link", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="access_logs", to="sharing.sharelink")),
            ],
            options={
                "ordering": ["-accessed_at"],
            },
        ),
    ]
