"""
Validatori password personalizzati (FASE 14).
"""
import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


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
