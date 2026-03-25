"""Documentazione OpenAPI pubblica."""
import pytest
from django.test import Client


@pytest.mark.django_db
def test_schema_endpoint_returns_200():
    c = Client()
    r = c.get("/api/schema/")
    assert r.status_code == 200


@pytest.mark.django_db
def test_swagger_ui_accessible():
    c = Client()
    r = c.get("/api/docs/")
    assert r.status_code == 200


@pytest.mark.django_db
def test_redoc_accessible():
    c = Client()
    r = c.get("/api/redoc/")
    assert r.status_code == 200
