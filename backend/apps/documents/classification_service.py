"""
Classificazione documenti rule-based + estrazione metadati (FASE 30).
"""
import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)


class DocumentClassificationService:
    """Keyword/pattern matching; LLM opzionale in llm_classifier."""

    CLASSIFICATION_RULES = [
        {
            "type": "delibera",
            "label": "Delibera",
            "keywords": ["delibera", "deliberazione", "organo collegiale", "consiglio", "giunta"],
            "patterns": [r"delibera(?:zione)?\s+n[.\s]*\d+"],
            "weight": 1.0,
        },
        {
            "type": "determina",
            "label": "Determina Dirigenziale",
            "keywords": ["determina", "determinazione", "dirigente", "dirigenziale"],
            "patterns": [r"determina(?:zione)?\s+n[.\s]*\d+"],
            "weight": 1.0,
        },
        {
            "type": "fattura",
            "label": "Fattura",
            "keywords": ["fattura", "invoice", "imponibile", "iva", "totale", "partita iva", "codice fiscale"],
            "patterns": [
                r"fattura\s+n[.\s]*\d+",
                r"p\.?\s*iva\s*\d+",
                r"tot(?:ale)?\s*€?\s*[\d.,]+",
            ],
            "weight": 1.0,
        },
        {
            "type": "contratto",
            "label": "Contratto",
            "keywords": ["contratto", "accordo", "convenzione", "stipulano", "parti contraenti", "clausol"],
            "patterns": [r"tra\s+le\s+parti", r"art(?:icolo)?\.?\s*\d+"],
            "weight": 0.8,
        },
        {
            "type": "circolare",
            "label": "Circolare",
            "keywords": ["circolare", "direttiva", "disposizione", "si comunica", "si dispone"],
            "patterns": [r"circolare\s+n[.\s]*\d+"],
            "weight": 1.0,
        },
        {
            "type": "verbale",
            "label": "Verbale",
            "keywords": ["verbale", "riunione", "seduta", "presenti", "assenti", "ordine del giorno"],
            "patterns": [r"verbale\s+(?:di|della)\s+", r"seduta\s+del\s+\d+"],
            "weight": 1.0,
        },
        {
            "type": "nota",
            "label": "Nota/Comunicazione",
            "keywords": ["nota", "comunicazione", "oggetto:", "spett.", "egregio", "gentile"],
            "patterns": [r"prot(?:ocollo)?\.?\s*n[.\s]*\d+"],
            "weight": 0.6,
        },
        {
            "type": "bando",
            "label": "Bando/Avviso",
            "keywords": ["bando", "avviso", "gara", "appalto", "procedura", "aggiudicazione", "offerta"],
            "patterns": [r"bando\s+(?:di|per)\s+", r"cig\s*[:\s]*[a-zA-Z0-9]+"],
            "weight": 1.0,
        },
        {
            "type": "relazione",
            "label": "Relazione/Report",
            "keywords": ["relazione", "report", "analisi", "sintesi", "conclusioni", "premessa"],
            "patterns": [],
            "weight": 0.5,
        },
    ]

    WORKFLOW_MAP = {
        "delibera": "approvazione_collegiale",
        "determina": "approvazione_dirigenziale",
        "fattura": "verifica_contabile",
        "contratto": "approvazione_legale",
        "bando": "approvazione_gara",
    }

    TITOLARIO_MAP = {
        "delibera": "1.1",
        "determina": "1.2",
        "fattura": "4.1",
        "contratto": "3.1",
        "circolare": "1.3",
        "bando": "5.1",
    }

    @classmethod
    def classify(cls, text: str, tenant_id: Optional[str] = None) -> dict[str, Any]:
        del tenant_id  # riservato a regole per-tenant future
        if not text or len(text.strip()) < 10:
            return cls._empty_result()

        text_lower = text.lower()
        scores = []
        for rule in cls.CLASSIFICATION_RULES:
            score = cls._score_rule(text_lower, rule)
            if score > 0:
                scores.append(
                    {
                        "type": rule["type"],
                        "label": rule["label"],
                        "confidence": min(float(score), 1.0),
                        "method": "rule_based",
                    }
                )

        scores.sort(key=lambda x: x["confidence"], reverse=True)
        suggestions = scores[:3]

        metadata = cls._extract_metadata(text)

        workflow_suggestion = None
        classification_suggestion = None
        if suggestions:
            top = suggestions[0]["type"]
            workflow_suggestion = cls.WORKFLOW_MAP.get(top)
            classification_suggestion = cls.TITOLARIO_MAP.get(top)

        return {
            "suggestions": suggestions,
            "metadata_suggestions": metadata,
            "workflow_suggestion": workflow_suggestion,
            "classification_suggestion": classification_suggestion,
        }

    @classmethod
    def _score_rule(cls, text_lower: str, rule: dict) -> float:
        kws = rule["keywords"]
        keyword_hits = sum(1 for kw in kws if kw in text_lower) if kws else 0
        keyword_score = (keyword_hits / len(kws)) * rule["weight"] if kws else 0.0

        patterns = rule.get("patterns") or []
        pattern_score = 0.0
        if patterns:
            pattern_hits = sum(1 for p in patterns if re.search(p, text_lower))
            pattern_score = (pattern_hits / len(patterns)) * 0.3

        return keyword_score + pattern_score

    @classmethod
    def _extract_metadata(cls, text: str) -> dict[str, str]:
        metadata: dict[str, str] = {}

        date_match = re.search(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})", text)
        if date_match:
            day, month, year = date_match.groups()
            metadata["date"] = f"{year}-{month.zfill(2)}-{day.zfill(2)}"

        prot_match = re.search(
            r"prot(?:ocollo)?\.?\s*(?:n\.?\s*)?(\d+(?:[/\-]\d+)?)",
            text,
            re.IGNORECASE,
        )
        if prot_match:
            metadata["protocol_number"] = prot_match.group(1)

        obj_match = re.search(r"oggetto\s*:\s*(.+?)(?:\n|$)", text, re.IGNORECASE)
        if obj_match:
            metadata["subject"] = obj_match.group(1).strip()[:200]

        mitt_match = re.search(
            r"(?:mittente|da|from)\s*:\s*(.+?)(?:\n|$)",
            text,
            re.IGNORECASE,
        )
        if mitt_match:
            metadata["sender"] = mitt_match.group(1).strip()[:200]

        amount_match = re.search(r"(?:€|EUR)\s*([\d.,]+(?:\.\d{2})?)", text)
        if not amount_match:
            amount_match = re.search(r"([\d.,]+)\s*(?:€|EUR|euro)", text, re.IGNORECASE)
        if amount_match:
            metadata["amount"] = amount_match.group(1).strip()

        piva_match = re.search(
            r"(?:p\.?\s*iva|partita\s+iva)\s*[:\s]*(\d{11})",
            text,
            re.IGNORECASE,
        )
        if piva_match:
            metadata["vat_number"] = piva_match.group(1)

        cf_match = re.search(
            r"(?:c\.?\s*f\.?|codice\s+fiscale)\s*[:\s]*([A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z])",
            text,
            re.IGNORECASE,
        )
        if cf_match:
            metadata["fiscal_code"] = cf_match.group(1).upper()

        return metadata

    @classmethod
    def _empty_result(cls) -> dict[str, Any]:
        return {
            "suggestions": [],
            "metadata_suggestions": {},
            "workflow_suggestion": None,
            "classification_suggestion": None,
        }
