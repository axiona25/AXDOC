# Copertura: file con pochi miss FASE 35D.4
import pytest


def test_protocols_agid_converter_import():
    from apps.protocols import agid_converter as m

    assert m is not None


def test_organizations_utils_import():
    from apps.organizations import utils as u

    assert u is not None


def test_notifications_signals_import():
    import apps.notifications.signals  # noqa: F401

    assert True
