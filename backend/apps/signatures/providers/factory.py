"""Factory per provider firma e conservazione (mock vs aruba)."""
from django.conf import settings

from .base import BaseSignatureProvider, BaseConservationProvider
from .mock_provider import MockSignatureProvider, MockConservationProvider
from .aruba_provider import ArubaSignatureProvider, ArubaConservationProvider


def get_signature_provider() -> BaseSignatureProvider:
    name = getattr(settings, "SIGNATURE_PROVIDER", "mock")
    if name == "aruba":
        return ArubaSignatureProvider()
    return MockSignatureProvider()


def get_conservation_provider() -> BaseConservationProvider:
    name = getattr(settings, "CONSERVATION_PROVIDER", "mock")
    if name == "aruba":
        return ArubaConservationProvider()
    return MockConservationProvider()
