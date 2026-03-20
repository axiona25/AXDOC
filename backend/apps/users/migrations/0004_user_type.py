# Generated for FASE 17 - user_type (internal/guest)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0003_usergroup_usergroupmembership"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="user_type",
            field=models.CharField(
                choices=[("internal", "Utente interno"), ("guest", "Utente ospite")],
                default="internal",
                help_text="Interno: accesso pieno; Ospite: solo documenti condivisi.",
                max_length=20,
            ),
        ),
    ]
