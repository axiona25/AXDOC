# Generated for AXDOC FASE 04 - Gruppi utenti (RF-016)

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0002_user_mfa_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserGroup",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=200, unique=True)),
                ("description", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_groups", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Gruppo utenti",
                "verbose_name_plural": "Gruppi utenti",
            },
        ),
        migrations.CreateModel(
            name="UserGroupMembership",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("added_at", models.DateTimeField(auto_now_add=True)),
                ("added_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="added_group_memberships", to=settings.AUTH_USER_MODEL)),
                ("group", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="memberships", to="users.usergroup")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="group_memberships", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Membro gruppo",
                "verbose_name_plural": "Membri gruppo",
                "unique_together": {("group", "user")},
            },
        ),
    ]
