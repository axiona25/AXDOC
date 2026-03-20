"""
MFA TOTP: generazione secret, QR, verifica codici, backup codes (RF-002, RNF-008).
"""
import hashlib
import base64
import pyotp
import qrcode
from io import BytesIO

TOTP_ISSUER = "AXDOC"
BACKUP_CODE_LENGTH = 8
BACKUP_CODE_COUNT = 8


def generate_totp_secret() -> str:
    """Genera un secret base32 casuale per TOTP."""
    return pyotp.random_base32()


def get_totp_uri(secret: str, email: str, issuer: str = TOTP_ISSUER) -> str:
    """URI otpauth per generare il QR code nell'app authenticator."""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=issuer)


def generate_qr_code_base64(totp_uri: str) -> str:
    """Genera immagine QR code come base64 PNG."""
    qr = qrcode.QRCode(version=1, box_size=4, border=4)
    qr.add_data(totp_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


def verify_totp(secret: str, code: str, window: int = 1) -> bool:
    """Verifica un codice TOTP a 6 cifre (window=1 → ±30s)."""
    if not secret or not code or len(code) != 6:
        return False
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=window)


def _hash_backup_code(code: str) -> str:
    """Hash SHA-256 del codice di recupero per storage."""
    return hashlib.sha256(code.encode()).hexdigest()


def generate_backup_codes() -> tuple[list[str], list[str]]:
    """Genera 8 codici di recupero. Ritorna (plain, hashed)."""
    import uuid
    plain = []
    hashed = []
    for _ in range(BACKUP_CODE_COUNT):
        raw = uuid.uuid4().hex[:BACKUP_CODE_LENGTH].upper()
        plain.append(raw)
        hashed.append(_hash_backup_code(raw))
    return plain, hashed


def verify_backup_code(stored_hashed_codes: list, provided_code: str) -> tuple[bool, list]:
    """
    Verifica un codice di recupero e rimuove quello usato dalla lista.
    Ritorna (ok, nuova_lista_hashed).
    """
    if not stored_hashed_codes or not provided_code:
        return False, list(stored_hashed_codes) if stored_hashed_codes else []
    provided_clean = provided_code.strip().upper()
    if len(provided_clean) != BACKUP_CODE_LENGTH:
        return False, list(stored_hashed_codes)
    h = _hash_backup_code(provided_clean)
    new_list = [x for x in stored_hashed_codes if x != h]
    if len(new_list) < len(stored_hashed_codes):
        return True, new_list
    return False, list(stored_hashed_codes)
