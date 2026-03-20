"""
Generazione indice PDF fascicolo conforme AGID art. 41 CAD (FASE 22).
"""
import hashlib
from io import BytesIO
from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def _draw_text(c, x, y, text, size=10):
    if not text:
        text = ""
    c.setFont("Helvetica", size)
    c.drawString(x, y, str(text)[:200])


def generate_dossier_index_pdf(dossier) -> bytes:
    """
    Genera indice PDF fascicolo con reportlab. Conforme AGID art. 41 CAD.
    Sezioni: Copertina, Tabella documenti, Tabella cartelle, Tabella email,
    Metadati AGID, Footer con hash e timestamp.
    """
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    y = height - 40 * mm

    # Copertina
    c.setFont("Helvetica-Bold", 14)
    c.drawString(20 * mm, y, "Indice del fascicolo")
    y -= 8 * mm
    c.setFont("Helvetica", 10)
    _draw_text(c, 20 * mm, y, f"Identificativo: {getattr(dossier, 'identifier', '')}")
    y -= 6 * mm
    _draw_text(c, 20 * mm, y, f"Oggetto: {getattr(dossier, 'title', '')}")
    y -= 6 * mm
    resp = getattr(dossier, "responsible", None)
    _draw_text(c, 20 * mm, y, f"Responsabile: {resp.email if resp else '—'}")
    y -= 6 * mm
    ou = getattr(dossier, "organizational_unit", None)
    _draw_text(c, 20 * mm, y, f"UO: {ou.code if ou else '—'}")
    y -= 6 * mm
    _draw_text(c, 20 * mm, y, f"Data apertura: {dossier.created_at.strftime('%d/%m/%Y') if getattr(dossier, 'created_at', None) else '—'}")
    y -= 6 * mm
    _draw_text(c, 20 * mm, y, f"Data chiusura: {dossier.closed_at.strftime('%d/%m/%Y') if getattr(dossier, 'closed_at', None) else '—'}")
    y -= 6 * mm
    _draw_text(c, 20 * mm, y, f"Classificazione: {getattr(dossier, 'classification_code', '')} {getattr(dossier, 'classification_label', '')}")
    y -= 12 * mm

    # Tabella documenti
    c.setFont("Helvetica-Bold", 11)
    c.drawString(20 * mm, y, "Documenti")
    y -= 6 * mm
    docs = list(dossier.dossier_documents.select_related("document").all()[:100])
    if docs:
        c.setFont("Helvetica", 8)
        for i, dd in enumerate(docs, 1):
            doc = dd.document
            title = getattr(doc, "title", "") or str(doc.id)
            _draw_text(c, 20 * mm, y, f"{i}. {title[:60]}")
            y -= 4 * mm
            if y < 40 * mm:
                c.showPage()
                y = height - 25 * mm
    else:
        _draw_text(c, 22 * mm, y, "Nessun documento.")
        y -= 6 * mm
    y -= 6 * mm

    # Tabella cartelle
    c.setFont("Helvetica-Bold", 11)
    c.drawString(20 * mm, y, "Cartelle collegate")
    y -= 6 * mm
    folders = []
    if hasattr(dossier, "dossier_folders"):
        folders = list(dossier.dossier_folders.select_related("folder").all()[:50])
    if folders:
        c.setFont("Helvetica", 8)
        for i, df in enumerate(folders, 1):
            name = df.folder.name if df.folder else str(df.folder_id)
            _draw_text(c, 22 * mm, y, f"{i}. {name[:60]}")
            y -= 4 * mm
            if y < 40 * mm:
                c.showPage()
                y = height - 25 * mm
    else:
        _draw_text(c, 22 * mm, y, "Nessuna cartella.")
        y -= 6 * mm
    y -= 6 * mm

    # Tabella email/PEC
    c.setFont("Helvetica-Bold", 11)
    c.drawString(20 * mm, y, "Email / PEC")
    y -= 6 * mm
    emails = []
    if hasattr(dossier, "dossier_emails"):
        emails = list(dossier.dossier_emails.all()[:50])
    if emails:
        c.setFont("Helvetica", 8)
        for i, em in enumerate(emails, 1):
            _draw_text(c, 22 * mm, y, f"{i}. [{em.email_type}] {em.subject[:50]} - {em.received_at.strftime('%d/%m/%Y')}")
            y -= 4 * mm
            if y < 40 * mm:
                c.showPage()
                y = height - 25 * mm
    else:
        _draw_text(c, 22 * mm, y, "Nessuna email.")
        y -= 6 * mm
    y -= 6 * mm

    # Metadati AGID
    c.setFont("Helvetica-Bold", 11)
    c.drawString(20 * mm, y, "Metadati AGID")
    y -= 6 * mm
    c.setFont("Helvetica", 8)
    from apps.metadata.agid_metadata import get_agid_metadata_for_dossier
    try:
        meta = get_agid_metadata_for_dossier(dossier)
        for k, v in (meta or {}).items():
            _draw_text(c, 22 * mm, y, f"{k}: {v}")
            y -= 4 * mm
            if y < 40 * mm:
                c.showPage()
                y = height - 25 * mm
    except Exception:
        _draw_text(c, 22 * mm, y, "Metadati non disponibili.")
        y -= 6 * mm
    y -= 8 * mm

    # Footer: hash e timestamp
    ts = timezone.now().isoformat()
    c.setFont("Helvetica", 8)
    c.drawString(20 * mm, 15 * mm, f"Timestamp generazione: {ts}")
    content_for_hash = f"{getattr(dossier, 'identifier', '')}{ts}"
    h = hashlib.sha256(content_for_hash.encode()).hexdigest()[:32]
    c.drawString(20 * mm, 12 * mm, f"Hash indice: {h}")

    c.save()
    buf.seek(0)
    return buf.getvalue()
