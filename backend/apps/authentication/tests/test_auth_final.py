# Copertura: authentication/* FASE 35D.3
import pytest
from django.contrib.auth import get_user_model

from apps.authentication import encryption
from apps.authentication import mfa, session_limit

User = get_user_model()


@pytest.mark.django_db
class TestAuthFinal:
    def test_encrypt_decrypt_secret(self):
        s = "mfa-secret-value"
        enc = encryption.encrypt_secret(s)
        assert encryption.decrypt_secret(enc) == s
        assert encryption.decrypt_secret("") == ""

    def test_mfa_totp_short_code(self):
        assert mfa.verify_totp("JBSWY3DPEHPK3PXP", "12") is False

    def test_backup_codes(self):
        plain, hashed = mfa.generate_backup_codes()
        assert len(plain) == mfa.BACKUP_CODE_COUNT
        ok, new_list = mfa.verify_backup_code(hashed, plain[0])
        assert ok is True

    def test_session_limit_noop(self):
        session_limit.limit_concurrent_refresh_sessions(None)
