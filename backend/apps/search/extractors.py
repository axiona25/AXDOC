"""
Estrazione testo da file per indicizzazione (FASE 12).
"""
import os


def extract_text(file_path, mime_type=None):
    """
    Estrae testo da file. Ritorna stringa vuota se tipo non supportato.
    """
    if not file_path or not os.path.isfile(file_path):
        return ""
    mime_type = (mime_type or "").lower()
    try:
        if mime_type.startswith("text/"):
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        if "pdf" in mime_type or (not mime_type and file_path.lower().endswith(".pdf")):
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            parts = []
            for page in reader.pages:
                try:
                    parts.append(page.extract_text() or "")
                except Exception:
                    parts.append("")
            return "\n".join(parts)
        if "wordprocessingml" in mime_type or "msword" in mime_type or (
            not mime_type and (file_path.lower().endswith(".docx") or file_path.lower().endswith(".doc"))
        ):
            try:
                from docx import Document as DocxDocument
                doc = DocxDocument(file_path)
                return "\n".join(p.text for p in doc.paragraphs)
            except Exception:
                return ""
        return ""
    except Exception:
        return ""
