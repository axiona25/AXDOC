# Generated manually for category + description on Protocol

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("protocols", "0003_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="protocol",
            name="category",
            field=models.CharField(
                choices=[
                    ("file", "Documento/File"),
                    ("email", "Email"),
                    ("pec", "PEC"),
                    ("other", "Altro"),
                ],
                default="file",
                help_text="Categoria del protocollo",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="protocol",
            name="description",
            field=models.TextField(blank=True, help_text="Descrizione estesa del protocollo"),
        ),
    ]
