"""Test health check endpoint (FASE 15)."""
import pytest
from django.test import Client


@pytest.mark.django_db
def test_health_returns_200_and_checks(client):
    """GET /api/health/ returns 200 with status and checks."""
    r = client.get("/api/health/")
    assert r.status_code == 200
    data = r.json()
    assert "status" in data
    assert data["status"] in ("healthy", "degraded", "unhealthy")
    assert "checks" in data
    assert "database" in data["checks"]
    assert "timestamp" in data
    assert "uptime_seconds" in data
