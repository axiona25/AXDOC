"""
Cifratura segreti MFA a riposo (Fernet) e campi modello cifrati.
"""
import base64
import hashlib

from cryptography.fernet import Fernet
from django.conf import settings
from django.core.validators import MaxLengthValidator
from django.db import models


def _get_fernet_key():
    """Deriva una chiave Fernet da SECRET_KEY."""
    key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return base64.urlsafe_b64encode(key)


def _get_fernet() -> Fernet:
    """Istanza Fernet condivisa (stessa chiave di encrypt_secret)."""
    return Fernet(_get_fernet_key())


def encrypt_secret(plaintext: str) -> str:
    """Cifra un segreto (es. mfa_secret) per storage nel DB."""
    if not plaintext:
        return ""
    f = Fernet(_get_fernet_key())
    return f.encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    """Decifra un segreto salvato nel DB."""
    if not ciphertext:
        return ""
    f = Fernet(_get_fernet_key())
    return f.decrypt(ciphertext.encode()).decode()


class EncryptedTextField(models.TextField):
    """
    Testo cifrato a riposo (Fernet). In DB il valore è opaco.
    Non indicizzabile; ricerca solo per uguaglianza esatta lato applicativo.
    """

    def get_prep_value(self, value):
        if value is None or value == "":
            return value
        f = _get_fernet()
        return f.encrypt(str(value).encode()).decode()

    def from_db_value(self, value, expression, connection):
        if value is None or value == "":
            return value
        try:
            f = _get_fernet()
            return f.decrypt(value.encode()).decode()
        except Exception:
            return value

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        return name, "apps.authentication.encryption.EncryptedTextField", args, kwargs


class EncryptedCharField(EncryptedTextField):
    """Come EncryptedTextField con max_length per validazione lato modello/form."""

    def __init__(self, *args, max_length=255, **kwargs):
        kwargs.pop("max_length", None)
        self.max_length = max_length
        super().__init__(*args, **kwargs)
        if max_length is not None:
            self.validators.append(MaxLengthValidator(int(max_length)))

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs["max_length"] = self.max_length
        return name, "apps.authentication.encryption.EncryptedCharField", args, kwargs
