"""
Conversione documenti protocollati in formato PDF/A con timbro AGID.
"""
import os
import subprocess
import tempfile
from datetime import datetime
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from pypdf import PdfReader, PdfWriter, Transformation


class ConversionError(Exception):
    """Errore durante conversione documento."""
    pass


class AGIDConverter:
    """Conversione e timbro documenti secondo linee guida AGID."""

    @staticmethod
    def convert_to_pdf(file_path: str) -> str:
        """
        Converte documento (DOCX, XLSX, ODP, ecc.) in PDF tramite LibreOffice headless.
        Ritorna il path del PDF generato.
        """
        if not os.path.isfile(file_path):
            raise ConversionError(f"File non trovato: {file_path}")
        output_dir = tempfile.mkdtemp()
        try:
            result = subprocess.run(
                [
                    "libreoffice",
                    "--headless",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    output_dir,
                    os.path.abspath(file_path),
                ],
                capture_output=True,
                timeout=60,
                cwd=output_dir,
            )
            if result.returncode != 0:
                stderr = (result.stderr or b"").decode("utf-8", errors="replace")
                raise ConversionError(f"LibreOffice conversion failed: {stderr}")
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            pdf_path = os.path.join(output_dir, f"{base_name}.pdf")
            if not os.path.isfile(pdf_path):
                raise ConversionError("LibreOffice non ha generato il file PDF.")
            return pdf_path
        except subprocess.TimeoutExpired:
            raise ConversionError("Timeout conversione LibreOffice (60s).")

    @staticmethod
    def generate_protocol_coverpage(protocol, output_path: str) -> str:
        """
        Genera una pagina di copertina PDF per il protocollo.
        Include metadati in formato tabellare. Conforme linee guida AGID.
        Ritorna output_path.
        """
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        y = height - 40 * mm
        c.setFont("Helvetica-Bold", 14)
        c.drawString(30 * mm, y, "COPERTINA PROTOCOLLO")
        y -= 12 * mm
        c.setFont("Helvetica", 10)
        _num = protocol.protocol_id or protocol.protocol_number
        _date = protocol.registered_at or protocol.protocol_date
        rows = [
            ("Numero protocollo", _num),
            ("Data e ora", _date.strftime("%d/%m/%Y %H:%M") if _date else "—"),
            ("Direzione", protocol.get_direction_display() if protocol else "—"),
            ("Unità organizzativa", protocol.organizational_unit.name if protocol.organizational_unit else "—"),
        ]
        for label, value in rows:
            c.drawString(30 * mm, y, f"{label}:")
            c.drawString(90 * mm, y, str(value or "—"))
            y -= 7 * mm
        y -= 5 * mm
        c.setFont("Helvetica", 8)
        c.drawString(30 * mm, y, "Documento generato in conformità alle linee guida AGID.")
        c.save()
        buffer.seek(0)
        with open(output_path, "wb") as f:
            f.write(buffer.getvalue())
        return output_path

    @staticmethod
    def _create_stamp_pdf(protocol, width_mm=180, height_mm=35) -> BytesIO:
        """Genera il PDF del solo timbro (una pagina) con reportlab."""
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=(width_mm * mm, height_mm * mm))
        c.setFont("Helvetica-Bold", 9)
        c.drawString(3 * mm, height_mm * mm - 6 * mm, "PROTOCOLLO")
        c.setFont("Helvetica", 8)
        _num = protocol.protocol_id or protocol.protocol_number
        _date = protocol.registered_at or protocol.protocol_date
        c.drawString(3 * mm, height_mm * mm - 12 * mm, f"Nr: {_num}")
        c.drawString(3 * mm, height_mm * mm - 18 * mm, f"Data: {_date.strftime('%d/%m/%Y %H:%M') if _date else '—'}")
        ou_name = protocol.organizational_unit.name if protocol.organizational_unit else "—"
        c.drawString(3 * mm, height_mm * mm - 24 * mm, f"U.O.: {ou_name[:40]}")
        c.drawString(3 * mm, height_mm * mm - 30 * mm, f"Direzione: {protocol.get_direction_display()}")
        c.save()
        buffer.seek(0)
        return buffer

    @staticmethod
    def apply_protocol_stamp(input_file_path: str, protocol, output_path: str) -> str:
        """
        Aggiunge timbro di protocollo al documento PDF.
        Timbro: numero, data, UO, direzione.
        Se il documento non è PDF: converte prima con LibreOffice.
        Ritorna output_path del file timbrato.
        """
        if not input_file_path.lower().endswith(".pdf"):
            input_file_path = AGIDConverter.convert_to_pdf(input_file_path)
        stamp_io = AGIDConverter._create_stamp_pdf(protocol)
        stamp_reader = PdfReader(stamp_io)
        stamp_page = stamp_reader.pages[0]
        reader = PdfReader(input_file_path)
        writer = PdfWriter()
        for i, page in enumerate(reader.pages):
            if i == 0:
                # Posiziona timbro in basso a sinistra (traslazione in punti: 1mm ≈ 2.83 pt)
                page.merge_transformed_page(
                    stamp_page,
                    Transformation().scale(1).translate(30 * 2.83, 20 * 2.83),
                    over=True,
                )
            writer.add_page(page)
        with open(output_path, "wb") as out:
            writer.write(out)
        return output_path
