# Generated manually for apps.mail

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("protocols", "0004_add_category_description"),
    ]

    operations = [
        migrations.CreateModel(
            name="MailAccount",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(help_text="Nome visualizzato (es: PEC Aziendale)", max_length=200)),
                (
                    "account_type",
                    models.CharField(
                        choices=[("email", "Email"), ("pec", "PEC")],
                        default="email",
                        max_length=10,
                    ),
                ),
                ("email_address", models.EmailField(max_length=254, unique=True)),
                ("imap_host", models.CharField(max_length=255)),
                ("imap_port", models.IntegerField(default=993)),
                ("imap_use_ssl", models.BooleanField(default=True)),
                ("imap_username", models.CharField(max_length=255)),
                ("imap_password", models.CharField(help_text="Cifrata a riposo in futuro", max_length=500)),
                ("smtp_host", models.CharField(max_length=255)),
                ("smtp_port", models.IntegerField(default=465)),
                ("smtp_use_ssl", models.BooleanField(default=True)),
                ("smtp_use_tls", models.BooleanField(default=False)),
                ("smtp_username", models.CharField(max_length=255)),
                ("smtp_password", models.CharField(max_length=500)),
                ("is_active", models.BooleanField(default=True)),
                ("is_default", models.BooleanField(default=False, help_text="Account predefinito per l'invio")),
                ("last_fetch_at", models.DateTimeField(blank=True, null=True)),
                ("last_fetch_uid", models.CharField(blank=True, help_text="Ultimo UID IMAP scaricato", max_length=100)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Account di posta",
                "verbose_name_plural": "Account di posta",
                "ordering": ["-is_default", "name"],
            },
        ),
        migrations.CreateModel(
            name="MailMessage",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("direction", models.CharField(choices=[("in", "Ricevuta"), ("out", "Inviata")], default="in", max_length=5)),
                ("message_id", models.CharField(blank=True, help_text="Message-ID header", max_length=500)),
                ("in_reply_to", models.CharField(blank=True, help_text="In-Reply-To header", max_length=500)),
                ("from_address", models.EmailField(max_length=254)),
                ("from_name", models.CharField(blank=True, max_length=300)),
                ("to_addresses", models.JSONField(default=list, help_text='[{"email": "...", "name": "..."}]')),
                ("cc_addresses", models.JSONField(blank=True, default=list)),
                ("bcc_addresses", models.JSONField(blank=True, default=list)),
                ("subject", models.CharField(blank=True, max_length=1000)),
                ("body_text", models.TextField(blank=True, help_text="Corpo in testo semplice")),
                ("body_html", models.TextField(blank=True, help_text="Corpo in HTML")),
                ("has_attachments", models.BooleanField(default=False)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("unread", "Non letta"),
                            ("read", "Letta"),
                            ("archived", "Archiviata"),
                            ("trash", "Cestinata"),
                        ],
                        default="unread",
                        max_length=20,
                    ),
                ),
                ("is_starred", models.BooleanField(default=False)),
                ("folder", models.CharField(default="INBOX", max_length=100)),
                ("imap_uid", models.CharField(blank=True, max_length=100)),
                ("sent_at", models.DateTimeField(blank=True, help_text="Data invio/ricezione dal header", null=True)),
                ("fetched_at", models.DateTimeField(auto_now_add=True)),
                (
                    "account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="messages",
                        to="mail.mailaccount",
                    ),
                ),
                (
                    "protocol",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="emails",
                        to="protocols.protocol",
                    ),
                ),
            ],
            options={
                "verbose_name": "Email",
                "verbose_name_plural": "Email",
                "ordering": ["-sent_at"],
            },
        ),
        migrations.CreateModel(
            name="MailAttachment",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("filename", models.CharField(max_length=500)),
                ("content_type", models.CharField(blank=True, max_length=200)),
                ("size", models.IntegerField(default=0)),
                ("file", models.FileField(upload_to="mail_attachments/%Y/%m/")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "message",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attachments",
                        to="mail.mailmessage",
                    ),
                ),
            ],
            options={
                "verbose_name": "Allegato email",
                "verbose_name_plural": "Allegati email",
            },
        ),
        migrations.AddIndex(
            model_name="mailmessage",
            index=models.Index(fields=["account", "folder", "sent_at"], name="mail_msg_acc_fld_sent"),
        ),
        migrations.AddIndex(
            model_name="mailmessage",
            index=models.Index(fields=["message_id"], name="mail_msg_message_id"),
        ),
    ]
