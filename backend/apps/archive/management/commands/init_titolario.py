"""
Inizializza il titolario (massimario di scarto) da TITOLARIO_DEFAULT.
Uso: python manage.py init_titolario
"""
from django.core.management.base import BaseCommand
from apps.archive.models import RetentionRule
from apps.archive.classification import TITOLARIO_DEFAULT


class Command(BaseCommand):
    help = "Crea RetentionRule dal titolario predefinito se non esistono"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Aggiorna anche le regole esistenti",
        )

    def handle(self, *args, **options):
        force = options["force"]
        created = 0
        updated = 0
        for node in TITOLARIO_DEFAULT:
            for ch in node.get("children", []):
                code = ch["code"]
                label = ch["label"]
                retention = ch.get("retention", 10)
                action = ch.get("action", "review")
                basis = ch.get("basis", "")
                rule, was_created = RetentionRule.objects.get_or_create(
                    classification_code=code,
                    defaults={
                        "classification_label": label,
                        "retention_years": retention,
                        "action_after_retention": action,
                        "retention_basis": basis,
                    },
                )
                if was_created:
                    created += 1
                elif force:
                    rule.classification_label = label
                    rule.retention_years = retention
                    rule.action_after_retention = action
                    rule.retention_basis = basis
                    rule.save()
                    updated += 1
        self.stdout.write(self.style.SUCCESS(f"Titolario: {created} regole create, {updated} aggiornate."))
