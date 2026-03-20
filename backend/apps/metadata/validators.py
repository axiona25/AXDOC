"""
Validazione valori metadati (RF-044).
"""
import re
from django.core.exceptions import ValidationError


def validate_metadata_values(structure, values):
    """
    Valida values rispetto ai campi della struttura.
    values: dict nome_campo -> valore
    Ritorna lista di dict: [{"field": "name", "message": "..."}, ...]
    """
    errors = []
    if not values:
        values = {}
    for field in structure.fields.all():
        value = values.get(field.name)
        err = _validate_field(field, value)
        if err:
            errors.append({"field": field.name, "message": err})
    return errors


def _validate_field(field, value):
    """Ritorna messaggio di errore o None se valido."""
    # Required
    if field.is_required:
        if value is None or value == "" or (isinstance(value, list) and len(value) == 0):
            return "Campo obbligatorio."

    # Se vuoto e non required, skip altre validazioni
    if value is None or value == "":
        return None
    if isinstance(value, list) and len(value) == 0:
        return None

    rules = field.validation_rules or {}
    ft = field.field_type

    if ft == "number":
        try:
            n = float(value) if value != "" else None
        except (TypeError, ValueError):
            return "Valore non numerico."
        if n is None:
            return None
        if "min" in rules and n < rules["min"]:
            return f"Valore minimo: {rules['min']}."
        if "max" in rules and n > rules["max"]:
            return f"Valore massimo: {rules['max']}."

    if ft in ("text", "textarea", "email", "phone", "url"):
        s = str(value).strip()
        if "min_length" in rules and len(s) < rules["min_length"]:
            return f"Lunghezza minima: {rules['min_length']} caratteri."
        if "max_length" in rules and len(s) > rules["max_length"]:
            return f"Lunghezza massima: {rules['max_length']} caratteri."
        if "regex" in rules:
            try:
                if not re.match(rules["regex"], s):
                    return "Formato non valido."
            except re.error:
                pass
        if ft == "email" and s:
            if "@" not in s or "." not in s.split("@")[-1]:
                return "Email non valida."

    if ft == "select":
        opts = [o.get("value") for o in (field.options or []) if o.get("value") is not None]
        if opts and value not in opts:
            return "Valore non consentito."

    if ft == "multiselect":
        opts = [o.get("value") for o in (field.options or []) if o.get("value") is not None]
        if not isinstance(value, list):
            value = [value] if value else []
        for v in value:
            if opts and v not in opts:
                return "Uno o più valori non consentiti."

    if ft == "boolean":
        if value is not None and value not in (True, False, "true", "false", 1, 0, "1", "0"):
            return "Valore booleano non valido."

    if ft in ("date", "datetime"):
        if value and not _looks_like_date(value):
            return "Data non valida."

    return None


def _looks_like_date(value):
    """Controllo approssimativo che value sia una data."""
    s = str(value)
    if not s:
        return True
    # ISO-like o solo numeri
    if "T" in s or "-" in s or "/" in s:
        return True
    return False
