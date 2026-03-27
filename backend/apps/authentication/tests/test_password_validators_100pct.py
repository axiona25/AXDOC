"""Copertura password_validators: policy DB, DynamicPasswordValidator, legacy validators."""
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError

from apps.authentication.password_validators import (
    DynamicPasswordValidator,
    SpecialCharPasswordValidator,
    UppercasePasswordValidator,
    _password_policy_from_db,
)


def test_password_policy_from_db_defaults():
    p = _password_policy_from_db()
    assert p["password_min_length"] == 8
    assert p["password_require_uppercase"] is True


def test_password_policy_from_db_exception_falls_back_empty():
    with patch(
        "apps.admin_panel.models.SystemSettings.get_settings",
        side_effect=RuntimeError("no db"),
    ):
        p = _password_policy_from_db()
    assert p["password_min_length"] == 8


@pytest.mark.django_db
def test_password_policy_merges_system_settings():
    from apps.admin_panel.models import SystemSettings

    s = SystemSettings.get_settings()
    sec = dict(s.security or {})
    sec.update(
        {
            "password_min_length": 10,
            "password_require_digit": False,
            "password_unknown_key": 1,
        }
    )
    s.security = sec
    s.save(update_fields=["security"])
    p = _password_policy_from_db()
    assert p["password_min_length"] == 10
    assert p["password_require_digit"] is False


def test_dynamic_validator_min_length():
    pol = {
        "password_min_length": 12,
        "password_require_uppercase": False,
        "password_require_lowercase": False,
        "password_require_digit": False,
        "password_require_special": False,
    }
    with patch("apps.authentication.password_validators._password_policy_from_db", return_value=pol):
        with pytest.raises(ValidationError):
            DynamicPasswordValidator().validate("short")
    with patch("apps.authentication.password_validators._password_policy_from_db", return_value=pol):
        DynamicPasswordValidator().validate("longenoughpass")


def test_dynamic_each_rule():
    v = DynamicPasswordValidator()
    off = {
        "password_min_length": 0,
        "password_require_uppercase": False,
        "password_require_lowercase": False,
        "password_require_digit": False,
        "password_require_special": False,
    }
    with patch(
        "apps.authentication.password_validators._password_policy_from_db",
        return_value={**off, "password_require_uppercase": True},
    ):
        with pytest.raises(ValidationError):
            v.validate("abcdef")
    with patch(
        "apps.authentication.password_validators._password_policy_from_db",
        return_value={**off, "password_require_lowercase": True},
    ):
        with pytest.raises(ValidationError):
            v.validate("ABCDEF")
    with patch(
        "apps.authentication.password_validators._password_policy_from_db",
        return_value={**off, "password_require_digit": True},
    ):
        with pytest.raises(ValidationError):
            v.validate("Abcdefgh")
    with patch(
        "apps.authentication.password_validators._password_policy_from_db",
        return_value={**off, "password_require_special": True},
    ):
        with pytest.raises(ValidationError):
            v.validate("Abcdefgh1")


def test_dynamic_get_help_text():
    assert DynamicPasswordValidator().get_help_text()


def test_uppercase_validator():
    with pytest.raises(ValidationError):
        UppercasePasswordValidator().validate("abc")
    UppercasePasswordValidator().validate("Abc")
    assert UppercasePasswordValidator().get_help_text()


def test_special_char_validator():
    with pytest.raises(ValidationError):
        SpecialCharPasswordValidator().validate("Abcdef1")
    SpecialCharPasswordValidator().validate("Abcdef1!")
    assert SpecialCharPasswordValidator().get_help_text()
