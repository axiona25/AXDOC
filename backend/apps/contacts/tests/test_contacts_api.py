"""Test API rubrica contatti (FASE 33)."""
import pytest
from rest_framework.test import APIClient

from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def admin_client(db):
    u = User.objects.create_user(
        email="contacts-admin@test.com",
        password="Test123!",
        role="ADMIN",
        first_name="A",
        last_name="D",
    )
    c = APIClient()
    c.force_authenticate(user=u)
    return c


@pytest.mark.django_db
class TestContactsAPI:
    def test_create_contact(self, admin_client):
        r = admin_client.post(
            "/api/contacts/",
            {
                "first_name": "Mario",
                "last_name": "Rossi",
                "email": "mario@example.com",
                "contact_type": "person",
            },
            format="json",
        )
        assert r.status_code == 201
        assert r.data["last_name"] == "Rossi"

    def test_list_contacts(self, admin_client):
        admin_client.post(
            "/api/contacts/",
            {
                "first_name": "Luigi",
                "last_name": "Verdi",
                "contact_type": "person",
            },
            format="json",
        )
        r = admin_client.get("/api/contacts/")
        assert r.status_code == 200
        assert len(r.data) >= 1

    def test_update_contact(self, admin_client):
        cr = admin_client.post(
            "/api/contacts/",
            {"first_name": "A", "last_name": "B", "contact_type": "person"},
            format="json",
        )
        cid = cr.data["id"]
        r = admin_client.patch(f"/api/contacts/{cid}/", {"notes": "aggiornato"}, format="json")
        assert r.status_code == 200
        assert r.data["notes"] == "aggiornato"

    def test_delete_contact(self, admin_client):
        cr = admin_client.post(
            "/api/contacts/",
            {"first_name": "X", "last_name": "Y", "contact_type": "person"},
            format="json",
        )
        cid = cr.data["id"]
        r = admin_client.delete(f"/api/contacts/{cid}/")
        assert r.status_code == 204

    def test_search_short_query_returns_empty_list(self, admin_client):
        r = admin_client.get("/api/contacts/search/", {"q": "a"})
        assert r.status_code == 200
        assert r.data == []
