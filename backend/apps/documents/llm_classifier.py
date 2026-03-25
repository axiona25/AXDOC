"""
Classificazione LLM opzionale (FASE 30). Predisposto senza chiamate API obbligatorie.
"""
from typing import Any

from django.conf import settings


class LLMClassifier:
    """Anthropic / OpenAI quando configurati."""

    @classmethod
    def is_available(cls) -> bool:
        return bool(
            getattr(settings, "ANTHROPIC_API_KEY", "")
            or getattr(settings, "OPENAI_API_KEY", "")
        )

    @classmethod
    def classify(cls, text: str, max_tokens: int = 500) -> dict[str, Any]:
        del max_tokens
        from .classification_service import DocumentClassificationService

        if not cls.is_available():
            return DocumentClassificationService._empty_result()
        # Implementazione API esplicita in seguito
        return DocumentClassificationService._empty_result()
