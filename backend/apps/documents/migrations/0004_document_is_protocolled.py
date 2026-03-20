# FASE 09: Blocco modifica documento protocollato (RF-063)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0003_alter_document_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="is_protocolled",
            field=models.BooleanField(default=False, help_text="Se True, il documento non è modificabile (RF-063)."),
        ),
    ]
