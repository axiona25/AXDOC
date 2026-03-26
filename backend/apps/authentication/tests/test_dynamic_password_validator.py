"""Policy password dinamica (FASE 32)."""
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.admin_panel.models import SystemSettings
from apps.authentication.password_validators import DynamicPasswordValidator

User = get_user_model()


class DynamicPasswordValidatorTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="pv@test.com",
            password="Xyz12345!",
            must_change_password=False,
        )
        self.v = DynamicPasswordValidator()
        obj = SystemSettings.get_settings()
        sec = dict(obj.security or {})
        sec.update(
            {
                "password_min_length": 8,
                "password_require_uppercase": True,
                "password_require_lowercase": True,
                "password_require_digit": True,
                "password_require_special": True,
            }
        )
        obj.security = sec
        obj.save(update_fields=["security"])

    def test_dynamic_password_validator_min_length(self):
        obj = SystemSettings.get_settings()
        obj.security = {**(obj.security or {}), "password_min_length": 12}
        obj.save(update_fields=["security"])
        with self.assertRaises(ValidationError):
            self.v.validate("Short1!a", user=self.user)

    def test_dynamic_password_validator_requires_uppercase(self):
        obj = SystemSettings.get_settings()
        obj.security = {**(obj.security or {}), "password_require_uppercase": True}
        obj.save(update_fields=["security"])
        with self.assertRaises(ValidationError):
            self.v.validate("lowercase1!", user=self.user)

    def test_dynamic_password_validator_all_disabled(self):
        obj = SystemSettings.get_settings()
        obj.security = {
            **(obj.security or {}),
            "password_min_length": 0,
            "password_require_uppercase": False,
            "password_require_lowercase": False,
            "password_require_digit": False,
            "password_require_special": False,
        }
        obj.save(update_fields=["security"])
        self.v.validate("abc", user=self.user)
