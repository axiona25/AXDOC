"""
Crea/aggiorna licenza di sistema.
Uso: python manage.py setup_license --org-name "Acme Corp" --max-users 50 [--expires 2026-12-31] [--features mfa,sso,ldap]
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.admin_panel.models import SystemLicense


class Command(BaseCommand):
    help = "Configura la licenza di sistema"

    def add_arguments(self, parser):
        parser.add_argument("--org-name", type=str, default="", help="Nome organizzazione")
        parser.add_argument("--expires", type=str, default=None, help="Data scadenza YYYY-MM-DD (vuoto = perpetua)")
        parser.add_argument("--max-users", type=int, default=None, help="Numero massimo utenti")
        parser.add_argument("--max-storage-gb", type=float, default=None, help="Storage massimo in GB")
        parser.add_argument("--features", type=str, default="", help="Feature abilitate separate da virgola (mfa,sso,ldap,...)")

    def handle(self, *args, **options):
        lic, _ = SystemLicense.objects.get_or_create(
            pk=1,
            defaults={
                "organization_name": options.get("org_name") or "Default",
                "activated_at": timezone.now().date(),
            },
        )
        if options.get("org_name"):
            lic.organization_name = options["org_name"]
        if options.get("expires"):
            from datetime import datetime
            lic.expires_at = datetime.strptime(options["expires"], "%Y-%m-%d").date()
        else:
            lic.expires_at = None
        if options.get("max_users") is not None:
            lic.max_users = options["max_users"]
        if options.get("max_storage_gb") is not None:
            lic.max_storage_gb = options["max_storage_gb"]
        if options.get("features"):
            feature_list = [f.strip().lower() for f in options["features"].split(",") if f.strip()]
            lic.features_enabled = {f: True for f in feature_list}
        lic.save()
        self.stdout.write(f"Licenza aggiornata: {lic.organization_name}, scadenza: {lic.expires_at or 'perpetua'}")
