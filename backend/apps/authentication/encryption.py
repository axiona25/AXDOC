"""
Cifratura segreti MFA a riposo (Fernet).
"""
import base64
import hashlib
from django.conf import settings
from cryptography.fernet import Fernet


def _get_fernet_key():
    """Deriva una chiave Fernet da SECRET_KEY."""
    key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return base64.urlsafe_b64encode(key)


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
