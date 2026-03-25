"""Classificazione rule-based e metadati (FASE 30)."""
import pytest

from apps.documents.classification_service import DocumentClassificationService


def test_classify_fattura_by_keywords():
    text = "Fattura n. 123 del 10/01/2025. Totale € 1.500,00. P.IVA 12345678901 imponibile IVA"
    r = DocumentClassificationService.classify(text)
    types = [s["type"] for s in r["suggestions"]]
    assert "fattura" in types


def test_classify_delibera_by_pattern():
    text = "Deliberazione n. 45 del consiglio comunale. La giunta ha approvato."
    r = DocumentClassificationService.classify(text)
    types = [s["type"] for s in r["suggestions"]]
    assert "delibera" in types


def test_extract_date_from_text():
    text = "Documento del 15/03/2024 per procedura."
    r = DocumentClassificationService.classify(text)
    assert r["metadata_suggestions"].get("date") == "2024-03-15"


def test_extract_protocol_number():
    text = "Prot. n. 2025/42 in data odierna."
    r = DocumentClassificationService.classify(text)
    pn = r["metadata_suggestions"].get("protocol_number")
    assert pn is not None
    assert "2025" in str(pn) or "42" in str(pn)


def test_extract_vat_number():
    text = "Partita IVA: 12345678901 sede legale"
    r = DocumentClassificationService.classify(text)
    assert r["metadata_suggestions"].get("vat_number") == "12345678901"


def test_empty_text_returns_empty_result():
    r = DocumentClassificationService.classify("")
    assert r["suggestions"] == []


def test_low_text_returns_empty_result():
    r = DocumentClassificationService.classify("short")
    assert r["suggestions"] == []
