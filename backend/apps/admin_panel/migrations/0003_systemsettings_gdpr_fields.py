# FASE 28 — campi GDPR su SystemSettings

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("admin_panel", "0002_systemsettings"),
    ]

    operations = [
        migrations.AddField(
            model_name="systemsettings",
            name="gdpr_audit_retention_days",
            field=models.IntegerField(
                default=1825,
                help_text="Retention audit log in giorni (default 5 anni)",
            ),
        ),
        migrations.AddField(
            model_name="systemsettings",
            name="gdpr_data_retention_days",
            field=models.IntegerField(
                default=3650,
                help_text="Retention documenti soft-deleted in giorni",
            ),
        ),
        migrations.AddField(
            model_name="systemsettings",
            name="gdpr_privacy_policy_url",
            field=models.URLField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="systemsettings",
            name="gdpr_privacy_policy_version",
            field=models.CharField(default="1.0", max_length=20),
        ),
    ]
