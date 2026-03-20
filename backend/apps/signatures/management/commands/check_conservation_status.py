"""Management command: aggiorna stato di tutte le richieste di conservazione pending."""
from django.core.management.base import BaseCommand
from apps.signatures.services import ConservationService


class Command(BaseCommand):
    help = "Aggiorna lo stato di tutte le richieste di conservazione sent/in_progress (da schedulare ogni ora)."

    def handle(self, *args, **options):
        result = ConservationService.check_all_pending()
        self.stdout.write(
            f"Checked: {result['checked']}, Updated: {result['updated']}, "
            f"Completed: {result['completed']}, Failed: {result['failed']}"
        )
