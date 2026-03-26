"""Edge case classificazione documenti (FASE 33)."""
import pytest

from apps.documents.classification_service import DocumentClassificationService


class TestClassificationEdgeCases:
    def test_mixed_type_document(self):
        text = (
            "Fattura n. 123 relativa al contratto di fornitura stipulato tra le parti. "
            "Totale € 100,00 IVA inclusa."
        )
        result = DocumentClassificationService.classify(text)
        assert len(result["suggestions"]) >= 2
        top = result["suggestions"][0]["type"]
        assert top in ("fattura", "contratto")

    def test_extract_first_date(self):
        text = "Roma, 15/03/2025. Riferimento al documento del 01/01/2024."
        result = DocumentClassificationService.classify(text)
        assert result["metadata_suggestions"].get("date") == "2025-03-15"

    def test_extract_amount_with_euro(self):
        text = "Totale fattura € 1.234,56 IVA inclusa"
        result = DocumentClassificationService.classify(text)
        assert "amount" in result["metadata_suggestions"]

    def test_unicode_text(self):
        text = "Delibera n. 42 dell'organo collegiale di lunedì 5 marzo"
        result = DocumentClassificationService.classify(text)
        assert len(result["suggestions"]) >= 1
        assert result["suggestions"][0]["type"] == "delibera"

    def test_very_long_text_no_crash(self):
        text = "fattura " * 5000
        result = DocumentClassificationService.classify(text)
        assert result["suggestions"][0]["type"] == "fattura"

    def test_html_in_text_no_crash(self):
        text = "<html><body><p>Fattura n. 123 P.IVA 12345678901</p></body></html>"
        result = DocumentClassificationService.classify(text)
        assert len(result["suggestions"]) > 0

    def test_short_text_empty(self):
        assert DocumentClassificationService.classify("abc")["suggestions"] == []
