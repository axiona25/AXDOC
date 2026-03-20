"""
Cifratura documenti on-demand AES-256-GCM (Documento Tecnico vDocs).
"""
import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes


class DocumentEncryption:
    """Cifratura/decifratura file con AES-256-GCM e chiave derivata da password."""

    @staticmethod
    def derive_key(password: str, salt: bytes) -> bytes:
        """Deriva chiave AES-256 da password tramite PBKDF2 (100k iterazioni)."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100_000,
        )
        return kdf.derive(password.encode("utf-8"))

    @staticmethod
    def encrypt_file(file_path: str, password: str) -> tuple[str, str]:
        """
        Cifra un file con AES-256-GCM.
        Ritorna: (encrypted_file_path, salt_b64).
        Il file cifrato ha estensione .enc
        """
        salt = os.urandom(16)
        key = DocumentEncryption.derive_key(password, salt)
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)

        with open(file_path, "rb") as f:
            plaintext = f.read()

        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        encrypted_path = file_path + ".enc"
        with open(encrypted_path, "wb") as f:
            f.write(salt + nonce + ciphertext)

        return encrypted_path, base64.b64encode(salt).decode("utf-8")

    @staticmethod
    def decrypt_file(encrypted_path: str, password: str) -> bytes:
        """
        Decifra file .enc. Ritorna i bytes del file originale.
        Solleva InvalidTag se password sbagliata.
        """
        with open(encrypted_path, "rb") as f:
            data = f.read()

        salt = data[:16]
        nonce = data[16:28]
        ciphertext = data[28:]

        key = DocumentEncryption.derive_key(password, salt)
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, ciphertext, None)
