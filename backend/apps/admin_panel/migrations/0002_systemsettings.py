# Generated for FASE 17 - SystemSettings

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("admin_panel", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="SystemSettings",
            fields=[
                ("id", models.PositiveSmallIntegerField(editable=False, primary_key=True, serialize=False, default=1)),
                ("email", models.JSONField(blank=True, default=dict)),
                ("organization", models.JSONField(blank=True, default=dict)),
                ("protocol", models.JSONField(blank=True, default=dict)),
                ("security", models.JSONField(blank=True, default=dict)),
                ("storage", models.JSONField(blank=True, default=dict)),
                ("ldap", models.JSONField(blank=True, default=dict)),
                ("conservation", models.JSONField(blank=True, default=dict)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Impostazioni di sistema",
                "verbose_name_plural": "Impostazioni di sistema",
            },
        ),
    ]
