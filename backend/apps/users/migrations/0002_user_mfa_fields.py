# Generated for AXDOC FASE 03 (MFA)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="mfa_enabled",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="user",
            name="mfa_secret",
            field=models.CharField(blank=True, max_length=256),
        ),
        migrations.AddField(
            model_name="user",
            name="mfa_backup_codes",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="user",
            name="mfa_setup_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
