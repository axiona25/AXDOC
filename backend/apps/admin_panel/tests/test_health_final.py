# FASE 35E.1 — Copertura: admin_panel/health_views.py
import json
from unittest.mock import patch

import pytest
from django.test.client import RequestFactory

from apps.admin_panel.health_views import HealthCheckView


def _json(resp):
    return json.loads(resp.content.decode())


@pytest.mark.django_db
class TestHealthCheckViewFinal:
    def test_health_ok(self):
        rf = RequestFactory()
        req = rf.get("/api/health/")
        resp = HealthCheckView.as_view()(req)
        assert resp.status_code in (200, 503)
        assert b"checks" in resp.content
        assert "status" in _json(resp)

    @patch("apps.admin_panel.health_views.connection")
    def test_database_error(self, mock_conn):
        mock_conn.ensure_connection.side_effect = Exception("db down")
        rf = RequestFactory()
        req = rf.get("/api/health/")
        resp = HealthCheckView.as_view()(req)
        assert resp.status_code == 503

    @patch("apps.admin_panel.health_views.connection")
    def test_migrations_pending_when_db_fails(self, mock_conn):
        mock_conn.ensure_connection.side_effect = Exception("db down")
        mock_conn.cursor.side_effect = Exception("no cursor")
        rf = RequestFactory()
        req = rf.get("/api/health/")
        resp = HealthCheckView.as_view()(req)
        data = _json(resp)
        assert data["checks"].get("database") == "error"

    @patch("redis.from_url")
    def test_redis_error(self, mock_from_url):
        mock_from_url.return_value.ping.side_effect = Exception("no redis")
        rf = RequestFactory()
        req = rf.get("/api/health/")
        resp = HealthCheckView.as_view()(req)
        assert _json(resp)["checks"]["redis"] == "error"

    @patch("apps.admin_panel.health_views.connection")
    def test_storage_exception(self, mock_conn):
        mock_conn.ensure_connection.return_value = None
        with patch("os.path.isdir", side_effect=OSError("x")):
            rf = RequestFactory()
            req = rf.get("/api/health/")
            resp = HealthCheckView.as_view()(req)
            assert _json(resp)["checks"]["storage"] == "error"
