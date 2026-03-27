"""Copertura completa apps.search.extractors.extract_text."""
import os
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def txt_file(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("hello utf8", encoding="utf-8")
    return str(p)


def test_extract_empty_path():
    from apps.search.extractors import extract_text

    assert extract_text("") == ""
    assert extract_text(None) == ""


def test_extract_missing_file(tmp_path):
    from apps.search.extractors import extract_text

    assert extract_text(str(tmp_path / "nope.bin")) == ""


def test_extract_plain_text_mime(txt_file):
    from apps.search.extractors import extract_text

    assert "hello" in extract_text(txt_file, "text/plain")


def test_extract_pdf_by_mime(tmp_path):
    from apps.search.extractors import extract_text

    p = tmp_path / "x.pdf"
    p.write_bytes(b"%PDF-1.4")
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "page one"
    mock_reader = MagicMock()
    mock_reader.pages = [mock_page]
    with patch("pypdf.PdfReader", return_value=mock_reader):
        assert "page one" in extract_text(str(p), "application/pdf")


def test_extract_pdf_by_extension_no_mime(tmp_path):
    from apps.search.extractors import extract_text

    p = tmp_path / "doc.pdf"
    p.write_bytes(b"%PDF-1.4")
    mock_reader = MagicMock()
    mock_page = MagicMock()
    mock_page.extract_text.side_effect = RuntimeError("x")
    mock_reader.pages = [mock_page]
    with patch("pypdf.PdfReader", return_value=mock_reader):
        out = extract_text(str(p), "")
        assert out == ""


def test_extract_docx_success(tmp_path):
    from apps.search.extractors import extract_text

    p = tmp_path / "w.docx"
    p.write_bytes(b"PK\x03\x04")
    para = MagicMock()
    para.text = "line"
    mock_doc = MagicMock()
    mock_doc.paragraphs = [para]
    with patch("docx.Document", return_value=mock_doc):
        assert "line" in extract_text(str(p), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")


def test_extract_docx_import_error_returns_empty(tmp_path):
    from apps.search.extractors import extract_text

    p = tmp_path / "w.docx"
    p.write_bytes(b"x")
    with patch("docx.Document", side_effect=OSError("bad")):
        assert extract_text(str(p), "application/msword") == ""


def test_extract_unsupported_type_returns_empty(tmp_path):
    from apps.search.extractors import extract_text

    p = tmp_path / "z.bin"
    p.write_bytes(b"data")
    assert extract_text(str(p), "application/octet-stream") == ""


def test_extract_outer_exception_returns_empty(txt_file):
    from apps.search.extractors import extract_text

    with patch("builtins.open", side_effect=OSError("boom")):
        assert extract_text(txt_file, "text/plain") == ""
