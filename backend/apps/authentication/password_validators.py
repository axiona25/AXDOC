"""
Validatori password personalizzati (FASE 14, FASE 32 policy dinamica).
"""
import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

_SPECIAL_CHARS_DEFAULT = "!@#$%^&*()_+-=[]{}|;:,.<>?"


def _password_policy_from_db():
    """Legge la policy da SystemSettings.security (chiavi password_*)."""
    defaults = {
        "password_min_length": 8,
        "password_require_uppercase": True,
        "password_require_lowercase": True,
        "password_require_digit": True,
        "password_require_special": True,
        "password_expiry_days": 0,
        "password_history_count": 0,
    }
    try:
        from apps.admin_panel.models import SystemSettings

        sec = SystemSettings.get_settings().security or {}
    except Exception:
        sec = {}
    out = defaults.copy()
    for k, v in sec.items():
        if k in defaults:
            out[k] = v
    return out


class DynamicPasswordValidator:
    """Validatore che applica lunghezza e complessità da impostazioni di sistema."""

    def validate(self, password, user=None):
        policy = _password_policy_from_db()
        messages = []

        min_len = int(policy.get("password_min_length") or 0)
        if min_len > 0 and len(password) < min_len:
            messages.append(
                _("La password deve avere almeno %(n)s caratteri.") % {"n": min_len}
            )

        if policy.get("password_require_uppercase", True):
            if not any(c.isupper() for c in password):
                messages.append(_("La password deve contenere almeno una lettera maiuscola."))

        if policy.get("password_require_lowercase", True):
            if not any(c.islower() for c in password):
                messages.append(_("La password deve contenere almeno una lettera minuscola."))

        if policy.get("password_require_digit", True):
            if not any(c.isdigit() for c in password):
                messages.append(_("La password deve contenere almeno un numero."))

        if policy.get("password_require_special", True):
            if not any(c in _SPECIAL_CHARS_DEFAULT for c in password):
                messages.append(
                    _("La password deve contenere almeno un carattere speciale (!@#$%% ecc.).")
                )

        if messages:
            raise ValidationError(messages)

    def get_help_text(self):
        return _("La password deve rispettare la policy configurata dall'amministratore.")


class UppercasePasswordValidator:
    """Richiede almeno un carattere maiuscolo."""

    def validate(self, password, user=None):
        if not re.search(r"[A-Z]", password):
            raise ValidationError(
                _("La password deve contenere almeno una lettera maiuscola."),
                code="password_no_upper",
            )

    def get_help_text(self):
        return _("La password deve contenere almeno una lettera maiuscola.")


class SpecialCharPasswordValidator:
    """Richiede almeno un carattere speciale (non alfanumerico)."""

    def validate(self, password, user=None):
        if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?`~]", password):
            raise ValidationError(
                _("La password deve contenere almeno un carattere speciale."),
                code="password_no_special",
            )

    def get_help_text(self):
        return _("La password deve contenere almeno un carattere speciale (!@#$%^&* ecc.).")
