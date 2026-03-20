"""
Sincronizza utenti da LDAP (RF-009).
Uso: python manage.py sync_ldap_users [--dry-run]
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = "Sincronizza utenti da LDAP"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Non applicare modifiche, solo report",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        if not getattr(settings, "LDAP_ENABLED", False):
            self.stdout.write("LDAP disabilitato. Nessuna azione.")
            return
        report = {"created": 0, "updated": 0, "disabled": 0, "errors": []}
        try:
            import ldap
            from django_auth_ldap.config import LDAPSearch
            conn = ldap.initialize(settings.AUTH_LDAP_SERVER_URI)
            conn.simple_bind_s(
                getattr(settings, "AUTH_LDAP_BIND_DN", ""),
                getattr(settings, "AUTH_LDAP_BIND_PASSWORD", ""),
            )
            base_dn = settings.AUTH_LDAP_USER_SEARCH.base_dn
            results = conn.search_s(base_dn, ldap.SCOPE_SUBTREE, "(objectClass=*)", ["mail", "givenName", "sn", "sAMAccountName"])
            conn.unbind_s()
            for dn, attrs in results:
                if dn is None or not isinstance(attrs, dict):
                    continue
                mail = (attrs.get("mail") or [b""])[0]
                if isinstance(mail, bytes):
                    mail = mail.decode("utf-8", errors="ignore")
                if not mail:
                    continue
                first_name = (attrs.get("givenName") or [b""])[0]
                if isinstance(first_name, bytes):
                    first_name = first_name.decode("utf-8", errors="ignore")
                last_name = (attrs.get("sn") or [b""])[0]
                if isinstance(last_name, bytes):
                    last_name = last_name.decode("utf-8", errors="ignore")
                if dry_run:
                    report["created"] += 1
                    continue
                user = User.objects.filter(email__iexact=mail).first()
                created = False
                if not user:
                    user = User.objects.create_user(
                        email=mail,
                        password="!",
                        first_name=first_name or "",
                        last_name=last_name or "",
                        role="OPERATOR",
                    )
                    user.set_unusable_password()
                    user.save(update_fields=["password"])
                    created = True
                if created:
                    user.set_unusable_password()
                    report["created"] += 1
                else:
                    user.first_name = first_name or user.first_name
                    user.last_name = last_name or user.last_name
                    user.save(update_fields=["first_name", "last_name"])
                    report["updated"] += 1
        except ImportError:
            report["errors"].append("django-auth-ldap non installato")
        except Exception as e:
            report["errors"].append(str(e))
        self.stdout.write(
            f"Report: created={report['created']}, updated={report['updated']}, "
            f"disabled={report['disabled']}, errors={report['errors']}"
        )
