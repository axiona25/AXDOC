"""
Importazione massiva utenti da CSV/Excel (RF-017).
"""
import csv
import io
from django.contrib.auth import get_user_model
from apps.organizations.models import OrganizationalUnit, OrganizationalUnitMembership

User = get_user_model()

IMPORT_COLUMNS = {
    "email": {"required": True, "type": "email"},
    "first_name": {"required": True, "type": "str", "max": 150},
    "last_name": {"required": True, "type": "str", "max": 150},
    "role": {
        "required": True,
        "type": "choice",
        "choices": ["OPERATOR", "REVIEWER", "APPROVER", "ADMIN"],
    },
    "organizational_unit_code": {"required": False, "type": "str"},
    "ou_role": {
        "required": False,
        "type": "choice",
        "choices": ["OPERATOR", "REVIEWER", "APPROVER"],
        "default": "OPERATOR",
    },
    "phone": {"required": False, "type": "str"},
}


class UserImporter:
    """Import utenti da CSV o Excel con validazione."""

    def parse_file(self, file_obj, file_type: str) -> list[dict]:
        """
        Parsa CSV o Excel. Ritorna lista di dict con le righe.
        file_type: 'csv' | 'xlsx'
        """
        if file_type == "csv":
            return self._parse_csv(file_obj)
        if file_type == "xlsx":
            return self._parse_xlsx(file_obj)
        raise ValueError("file_type deve essere 'csv' o 'xlsx'")

    def _parse_csv(self, file_obj) -> list[dict]:
        content = file_obj.read()
        if isinstance(content, bytes):
            content = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(content))
        headers = [h.strip().lower().replace(" ", "_") for h in (reader.fieldnames or [])]
        rows = []
        for row in reader:
            row_clean = {}
            for i, key in enumerate(reader.fieldnames or []):
                k = key.strip().lower().replace(" ", "_")
                if k in IMPORT_COLUMNS:
                    row_clean[k] = (row.get(key) or "").strip()
            rows.append(row_clean)
        return rows

    def _parse_xlsx(self, file_obj) -> list[dict]:
        import tablib
        content = file_obj.read() if hasattr(file_obj, "read") else file_obj
        data = tablib.Dataset().load(content, format="xlsx")
        if not data.headers:
            return []
        headers_lower = [str(h).strip().lower().replace(" ", "_") for h in data.headers]
        rows = []
        for row in data:
            row_d = dict(zip(headers_lower, row)) if len(row) == len(headers_lower) else {}
            row_clean = {
                k: str(v).strip() if v is not None else ""
                for k, v in row_d.items()
                if k in IMPORT_COLUMNS
            }
            rows.append(row_clean)
        return rows

    def validate_row(self, row: dict, row_number: int, check_existing: bool = True) -> list[str]:
        """
        Valida una singola riga. Ritorna lista di errori (vuota se OK).
        """
        errors = []
        for key, config in IMPORT_COLUMNS.items():
            value = (row.get(key) or "").strip()
            if config["required"] and not value:
                errors.append(f"{key}: obbligatorio")
                continue
            if not value and not config["required"]:
                continue
            if config["type"] == "email":
                if "@" not in value or "." not in value.split("@")[-1]:
                    errors.append("email: formato non valido")
                elif check_existing and User.objects.filter(email__iexact=value, is_deleted=False).exists():
                    errors.append("email: già esistente nel sistema")
            elif config["type"] == "str":
                max_len = config.get("max", 255)
                if len(value) > max_len:
                    errors.append(f"{key}: massimo {max_len} caratteri")
            elif config["type"] == "choice":
                if value.upper() not in [c.upper() for c in config["choices"]]:
                    errors.append(f"{key}: valore non valido (ammessi: {', '.join(config['choices'])})")
        ou_code = (row.get("organizational_unit_code") or "").strip()
        if ou_code and not OrganizationalUnit.objects.filter(code=ou_code, is_active=True).exists():
            errors.append("organizational_unit_code: UO non trovata")
        return errors

    def import_users(
        self,
        rows: list[dict],
        send_invite: bool = True,
        created_by=None,
    ) -> dict:
        """
        Importa utenti validati.
        Ritorna: total, created, skipped, errors.
        """
        from django.core.mail import send_mail
        from django.conf import settings
        from apps.authentication.models import UserInvitation, AuditLog
        from django.utils import timezone
        from datetime import timedelta

        result = {"total": len(rows), "created": 0, "skipped": 0, "errors": []}
        for i, row in enumerate(rows):
            row_number = i + 1
            errs = self.validate_row(row, row_number, check_existing=False)
            if errs:
                result["errors"].append({
                    "row": row_number,
                    "email": row.get("email", ""),
                    "errors": errs,
                })
                continue
            email = row.get("email", "").strip().lower()
            if User.objects.filter(email__iexact=email, is_deleted=False).exists():
                result["skipped"] += 1
                continue
            first_name = (row.get("first_name") or "").strip()[:150]
            last_name = (row.get("last_name") or "").strip()[:150]
            role = (row.get("role") or "OPERATOR").strip().upper()
            if role not in ["OPERATOR", "REVIEWER", "APPROVER", "ADMIN"]:
                role = "OPERATOR"
            phone = (row.get("phone") or "").strip()[:30]
            ou_role = (row.get("ou_role") or "OPERATOR").strip().upper()
            if ou_role not in ["OPERATOR", "REVIEWER", "APPROVER"]:
                ou_role = "OPERATOR"
            user = User.objects.create_user(
                email=email,
                password=None,
                first_name=first_name,
                last_name=last_name,
                role=role,
                phone=phone,
                must_change_password=True,
                created_by=created_by,
            )
            user.set_unusable_password()
            user.save(update_fields=["password"])
            ou_code = (row.get("organizational_unit_code") or "").strip()
            if ou_code:
                ou = OrganizationalUnit.objects.filter(code=ou_code, is_active=True).first()
                if ou:
                    OrganizationalUnitMembership.objects.get_or_create(
                        user=user,
                        organizational_unit=ou,
                        defaults={"role": ou_role, "is_active": True},
                    )
            result["created"] += 1
            if send_invite:
                inv = UserInvitation.objects.create(
                    email=user.email,
                    invited_by=created_by,
                    role=user.role,
                    ou_role=ou_role,
                    organizational_unit=OrganizationalUnit.objects.filter(code=ou_code, is_active=True).first() if ou_code else None,
                    expires_at=timezone.now() + timedelta(days=7),
                )
                frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
                link = f"{frontend_url}/accept-invitation/{inv.token}"
                send_mail(
                    subject="Invito a AXDOC",
                    message=f"Sei stato aggiunto a AXDOC. Clicca per attivare il tuo account (valido 7 giorni):\n{link}",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=True,
                )
        return result

    @staticmethod
    def get_template_csv() -> str:
        """Ritorna CSV template con header e riga esempio."""
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(["email", "first_name", "last_name", "role", "organizational_unit_code", "ou_role", "phone"])
        writer.writerow([
            "mario.rossi@esempio.it",
            "Mario",
            "Rossi",
            "OPERATOR",
            "",
            "OPERATOR",
            "",
        ])
        return out.getvalue()

    @staticmethod
    def get_template_xlsx() -> bytes:
        """Ritorna Excel template con header e riga esempio."""
        import tablib
        data = tablib.Dataset(
            headers=["email", "first_name", "last_name", "role", "organizational_unit_code", "ou_role", "phone"],
        )
        data.append(["mario.rossi@esempio.it", "Mario", "Rossi", "OPERATOR", "", "OPERATOR", ""])
        return data.export("xlsx")