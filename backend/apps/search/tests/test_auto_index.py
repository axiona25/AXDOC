"""Indicizzazione automatica su nuova DocumentVersion (FASE 37)."""
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.documents.models import Document, DocumentVersion, Folder

User = get_user_model()


@pytest.mark.django_db
def test_new_document_version_triggers_indexing():
    user = User.objects.create_user(email="idx1@test.com", password="test")
    folder = Folder.objects.create(name="F1")
    doc = Document.objects.create(
        title="Doc",
        folder=folder,
        created_by=user,
        status=Document.STATUS_DRAFT,
        current_version=1,
    )
    up = SimpleUploadedFile("a.txt", b"hello", content_type="text/plain")

    class _SyncThread:
        def __init__(self, target=None, daemon=True):
            self._target = target

        def start(self):
            if self._target:
                self._target()

    with patch("apps.search.tasks.index_document") as mock_idx:
        with patch("apps.search.signals.threading.Thread", _SyncThread):
            v = DocumentVersion.objects.create(
                document=doc,
                version_number=1,
                file=up,
                file_name="a.txt",
                file_type="text/plain",
                created_by=user,
            )
            assert v.pk
    mock_idx.assert_called_once_with(str(v.pk))


@pytest.mark.django_db
def test_update_version_does_not_reindex():
    user = User.objects.create_user(email="idx2@test.com", password="test")
    folder = Folder.objects.create(name="F2")
    doc = Document.objects.create(
        title="Doc2",
        folder=folder,
        created_by=user,
        status=Document.STATUS_DRAFT,
        current_version=1,
    )
    up = SimpleUploadedFile("b.txt", b"x", content_type="text/plain")
    v = DocumentVersion.objects.create(
        document=doc,
        version_number=1,
        file=up,
        file_name="b.txt",
        file_type="text/plain",
        created_by=user,
    )
    with patch("apps.search.tasks.index_document") as mock_idx:
        v.change_description = "edit"
        v.save(update_fields=["change_description"])
    mock_idx.assert_not_called()


@pytest.mark.django_db
def test_version_without_file_skipped():
    user = User.objects.create_user(email="idx3@test.com", password="test")
    folder = Folder.objects.create(name="F3")
    doc = Document.objects.create(
        title="Doc3",
        folder=folder,
        created_by=user,
        status=Document.STATUS_DRAFT,
        current_version=1,
    )
    with patch("apps.search.tasks.index_document") as mock_idx:
        DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="",
            file_type="",
            created_by=user,
        )
    mock_idx.assert_not_called()
