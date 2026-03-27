"""LLMClassifier: disponibilità e classify senza API obbligatoria."""
import pytest
from django.test.utils import override_settings

from apps.documents.llm_classifier import LLMClassifier


class TestLLMClassifier:
    def test_is_available_false_without_keys(self, settings):
        settings.ANTHROPIC_API_KEY = ""
        settings.OPENAI_API_KEY = ""
        assert LLMClassifier.is_available() is False

    @override_settings(ANTHROPIC_API_KEY="sk-test")
    def test_is_available_with_anthropic(self):
        assert LLMClassifier.is_available() is True

    @override_settings(ANTHROPIC_API_KEY="", OPENAI_API_KEY="sk-openai")
    def test_is_available_with_openai_only(self):
        assert LLMClassifier.is_available() is True

    def test_classify_returns_empty_when_unavailable(self, settings):
        settings.ANTHROPIC_API_KEY = ""
        settings.OPENAI_API_KEY = ""
        r = LLMClassifier.classify("any text")
        assert r["suggestions"] == []
        assert r.get("metadata_suggestions") == {}

    @override_settings(ANTHROPIC_API_KEY="k")
    def test_classify_when_available_returns_empty_stub(self):
        r = LLMClassifier.classify("doc text", max_tokens=100)
        assert r["suggestions"] == []
