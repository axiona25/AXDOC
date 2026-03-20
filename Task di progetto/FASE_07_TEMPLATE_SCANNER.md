# AXDOC — FASE 07
# Template Documentali, Conversione AGID e Scanner OCR

## Fonte nei documenti di analisi

**Conversione documenti AGID** — Documento Collaudo, segnalazioni:
> "Conversione dei documenti protocollati secondo guida Agid"

**Template documentali** — requisiti_documentale_estesi.docx:
> RF-047: Template documentali

**Template da struttura metadati** — AXDOC.docx:
> "un template per la compilazione dinamica dei documenti"

**Creazione PDF da scansione** — Documento Tecnico vDocs:
> "Creare Pdf da scannerizzazioni di documenti."
> "suite ImageMagik"

**Creazione e modifica documenti** — AXDOC.docx:
> "Documento che può essere di testo, di calcolo o una presentazione 
> gestiti con una libreria open source resa disponibile all'interno del programma."

**Nessuna di queste funzionalità è presente nelle fasi precedenti.**

**Prerequisito: FASE 06 completata.**

---

## CHECKLIST DI COMPLETAMENTO

- [ ] Conversione protocollo in formato PDF/A conforme AGID
- [ ] Timbro digitale su documento protocollato (numero, data, UO)
- [ ] Template documentali collegati a strutture metadati (RF-047)
- [ ] Compilazione dinamica template con valori metadati
- [ ] Download documento da template compilato
- [ ] Upload immagini scansionate → creazione PDF (Pillow/img2pdf)
- [ ] OCR su immagini scansionate (Tesseract)
- [ ] Editor testo base inline (integrazione OnlyOffice o TipTap)
- [ ] Tutti i test passano

---

## STEP 9E.1 — Conversione Documenti AGID

### Prompt per Cursor:

```
Implementa la conversione di documenti protocollati in formato PDF/A 
con timbro digitale conforme alle linee guida AGID.

Fonte: Documento Collaudo — "Conversione dei documenti protocollati secondo guida Agid"

Installa in requirements.txt:
  - reportlab==4.1.*      # generazione PDF/A
  - pypdf==4.1.*          # manipolazione PDF esistenti
  - Pillow (già presente)

Crea `backend/apps/protocols/agid_converter.py`:

class AGIDConverter:
  
  @staticmethod
  def apply_protocol_stamp(
    input_file_path: str,
    protocol: Protocol,
    output_path: str
  ) -> str:
    """
    Aggiunge timbro di protocollo al documento PDF.
    Il timbro include:
    - Numero protocollo (es. "2024/IT/0042")
    - Data e ora di protocollazione
    - Unità Organizzativa
    - Direzione (In entrata / In uscita)
    - Logo/nome organizzazione (da settings)
    
    Se il documento non è PDF: converte prima in PDF tramite LibreOffice.
    Ritorna il path del file timbrato.
    """
    # 1. Se non è PDF, converti
    if not input_file_path.endswith('.pdf'):
      input_file_path = AGIDConverter.convert_to_pdf(input_file_path)
    
    # 2. Apri PDF con pypdf
    # 3. Aggiungi pagina con timbro (o watermark sulla prima pagina)
    # 4. Usa reportlab per generare il timbro come PDF overlay
    # 5. Mergia i due PDF con pypdf PdfMerger/PdfWriter
    # 6. Salva output_path
    # 7. Ritorna output_path
  
  @staticmethod
  def convert_to_pdf(file_path: str) -> str:
    """
    Converte documento (DOCX, XLSX, ODP) in PDF tramite LibreOffice headless.
    Usa: libreoffice --headless --convert-to pdf --outdir /tmp file.docx
    Ritorna il path del PDF generato.
    """
    import subprocess
    import tempfile
    
    output_dir = tempfile.mkdtemp()
    result = subprocess.run([
      'libreoffice', '--headless', '--convert-to', 'pdf',
      '--outdir', output_dir, file_path
    ], capture_output=True, timeout=60)
    
    if result.returncode != 0:
      raise ConversionError(f"LibreOffice conversion failed: {result.stderr.decode()}")
    
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    return os.path.join(output_dir, f"{base_name}.pdf")
  
  @staticmethod
  def generate_protocol_coverpage(protocol: Protocol) -> str:
    """
    Genera una pagina di copertina PDF per il protocollo.
    Include tutti i metadati del protocollo in formato tabellare.
    Conforme alle linee guida AGID per i documenti protocollati.
    Ritorna path del PDF generato.
    """

Aggiungi endpoint in ProtocolViewSet:

GET /api/protocols/{id}/stamped_document/:
  - Scarica documento con timbro AGID applicato
  - Se protocollo senza documento allegato: genera coverpage
  - Se documento presente: applica timbro sul PDF
  - Crea AuditLog: action='protocol_document_downloaded_stamped'
  - Risponde: FileResponse con nome file "protocollo_{id}.pdf"

GET /api/protocols/{id}/coverpage/:
  - Genera e scarica pagina di copertina PDF del protocollo
  - Sempre disponibile indipendentemente da documento allegato

Aggiungi a `docker-compose.yml` nel backend service:
  - Verifica che LibreOffice sia installato nell'immagine Docker
  In backend/Dockerfile:
    RUN apt-get update && apt-get install -y libreoffice-writer libreoffice-calc \
        libreoffice-impress poppler-utils && apt-get clean

TEST `backend/apps/protocols/tests/test_agid.py`:
  - apply_protocol_stamp su PDF di test → output PDF con timbro
  - convert_to_pdf su file .txt → PDF generato
  - generate_protocol_coverpage → PDF valido con dati protocollo
  - Endpoint /stamped_document/: risponde con PDF

Esegui: `pytest backend/apps/protocols/tests/test_agid.py -v`
```

---

## STEP 9E.2 — Template Documentali

### Prompt per Cursor:

```
Implementa i template documentali collegati alle strutture metadati (RF-047).

Un template è un documento DOCX con segnaposto {{campo}} che vengono
sostituiti con i valori dei metadati del documento alla compilazione.

Installa in requirements.txt:
  - python-docx==1.1.*     # manipolazione DOCX
  - jinja2==3.1.*          # motore template per sostituzione variabili

Modifica `backend/apps/metadata/models.py`:
  Aggiungi in MetadataStructure:
  - template_file: FileField upload_to='templates/' null=True
    (file DOCX con segnaposto {{field_name}})
  - template_instructions: TextField blank=True
    (istruzioni per compilare il template)

Crea `backend/apps/metadata/template_engine.py`:

class DocumentTemplateEngine:
  
  AVAILABLE_PLACEHOLDERS = {
    # Dati documento
    '{{document.title}}': 'Titolo del documento',
    '{{document.created_at}}': 'Data creazione',
    '{{document.created_by}}': 'Autore',
    '{{document.version}}': 'Versione corrente',
    '{{document.status}}': 'Stato documento',
    # Dati utente
    '{{user.full_name}}': 'Nome completo utente',
    '{{user.email}}': 'Email utente',
    '{{user.organizational_unit}}': 'Unità organizzativa',
    # Data corrente
    '{{date.today}}': 'Data odierna (gg/mm/aaaa)',
    '{{date.now}}': 'Data e ora corrente',
    # Metadati (dinamici da struttura)
    '{{meta.nome_campo}}': 'Valore del campo metadato',
  }
  
  @staticmethod
  def fill_template(
    template_path: str,
    document: Document,
    user: User,
    output_path: str
  ) -> str:
    """
    Riempie il template DOCX con i valori del documento e metadati.
    - Apre template con python-docx
    - Per ogni paragrafo e cella tabella: sostituisce tutti i segnaposto
    - Usa Jinja2 per la logica condizionale nei template (es. {% if meta.tipo == "Contratto" %})
    - Salva il file compilato in output_path
    - Ritorna output_path
    """
    
    context = {
      'document': {
        'title': document.title,
        'created_at': document.created_at.strftime('%d/%m/%Y'),
        'created_by': document.created_by.get_full_name(),
        'version': document.current_version,
        'status': document.get_status_display(),
      },
      'user': {
        'full_name': user.get_full_name(),
        'email': user.email,
        'organizational_unit': user.get_primary_ou_name(),
      },
      'date': {
        'today': datetime.now().strftime('%d/%m/%Y'),
        'now': datetime.now().strftime('%d/%m/%Y %H:%M'),
      },
      'meta': document.metadata_values or {},
    }
    
    # Usa python-docx per aprire, Jinja2 per sostituire testo nei paragrafi
    # Gestisce anche header, footer e celle tabella
    # Output: file DOCX compilato
  
  @staticmethod
  def get_template_preview(metadata_structure: MetadataStructure) -> dict:
    """
    Ritorna lista dei segnaposto disponibili per questa struttura,
    con nome tecnico e descrizione.
    """

Aggiungi endpoint:

POST /api/metadata/structures/{id}/upload_template/:
  - Solo ADMIN
  - Upload file DOCX come template
  - Valida che sia un file .docx valido
  - Analizza i segnaposto presenti nel file
  - Salva in MetadataStructure.template_file
  - Risponde: { "placeholders_found": ["{{meta.fornitore}}", "{{document.title}}", ...] }

GET /api/metadata/structures/{id}/template_info/:
  - Lista segnaposto disponibili per questa struttura
  - Segnaposto trovati nel template (se caricato)
  - Download template originale

GET /api/documents/{id}/fill_template/:
  - Documento deve avere metadata_structure con template_file
  - Chiama DocumentTemplateEngine.fill_template(...)
  - Risponde con il file DOCX compilato (download)
  - Content-Disposition: attachment; filename="{titolo_documento}_compilato.docx"

Frontend — aggiornamenti:

MetadataStructureForm.tsx (Fase 4):
  Aggiungi sezione "Template documentale":
  - Upload area per file DOCX
  - Dopo upload: mostra segnaposto trovati nel template
  - Lista segnaposto disponibili con copia rapida ({{meta.nome_campo}})
  - Istruzioni: "Inserisci questi segnaposto nel tuo documento Word"
  - Bottone "Scarica template" per riscaricare il template caricato

DocumentDetailPanel.tsx:
  - Se documento ha struttura con template: aggiungi azione "Compila template"
  - Click → download del DOCX compilato con i valori del documento

TEST:
  - Upload template DOCX: segnaposto rilevati
  - fill_template: valori metadati sostituiti correttamente
  - fill_template senza template caricato → 400
  - Segnaposto non trovato nel documento → lasciato vuoto (no errore)

Esegui: `pytest backend/apps/metadata/tests/test_templates.py -v`
```

---

## STEP 9E.3 — PDF da Scansione e OCR

### Prompt per Cursor:

```
Implementa la creazione di PDF da immagini scansionate con OCR (Documento Tecnico vDocs).

"Creare Pdf da scannerizzazioni di documenti" + "suite ImageMagik"

Installa in requirements.txt:
  - img2pdf==0.5.*         # conversione immagini → PDF
  - pytesseract==0.3.*     # OCR wrapper per Tesseract
  - Pillow (già presente)

In backend/Dockerfile aggiungi:
  RUN apt-get install -y tesseract-ocr tesseract-ocr-ita tesseract-ocr-eng \
      imagemagick img2pdf && apt-get clean

Crea `backend/apps/documents/scanner.py`:

class DocumentScanner:
  
  SUPPORTED_IMAGE_FORMATS = ['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.gif']
  
  @staticmethod
  def images_to_pdf(image_paths: list[str], output_path: str) -> str:
    """
    Converte lista di immagini in un unico PDF.
    Usa img2pdf per conversione lossless delle immagini.
    Ritorna output_path del PDF generato.
    """
    with open(output_path, 'wb') as pdf_file:
      pdf_file.write(img2pdf.convert(image_paths))
    return output_path
  
  @staticmethod
  def ocr_image(image_path: str, language: str = 'ita+eng') -> str:
    """
    Esegue OCR su immagine tramite Tesseract.
    Ritorna il testo estratto.
    language: 'ita' per italiano, 'ita+eng' per bilingue
    """
    image = Image.open(image_path)
    # Pre-processing: converti in scala di grigi, aumenta contrasto
    image = image.convert('L')
    return pytesseract.image_to_string(image, lang=language)
  
  @staticmethod
  def enhance_scan(image_path: str, output_path: str) -> str:
    """
    Migliora qualità scansione:
    - Deskew (raddrizza)
    - Denoise
    - Contrasto adattivo
    Usa Pillow per operazioni base.
    """
    image = Image.open(image_path)
    image = image.convert('L')  # grayscale
    # Auto-contrasto
    from PIL import ImageOps, ImageFilter
    image = ImageOps.autocontrast(image)
    image = image.filter(ImageFilter.SHARPEN)
    image.save(output_path)
    return output_path

Aggiungi endpoint in DocumentViewSet:

POST /api/documents/scan_to_pdf/:
  Crea un nuovo documento da immagini scansionate.
  - Multipart con: images[] (lista file immagine), title, folder_id, 
    metadata_structure_id, perform_ocr (bool, default True)
  - Valida: max 50 immagini, max 10MB per immagine, formati supportati
  - Per ogni immagine: chiama enhance_scan per miglioramento
  - Chiama images_to_pdf → PDF unificato
  - Se perform_ocr=True: esegui OCR su ogni immagine, testo concatenato
    → salva in DocumentIndex per ricerca full-text (integrazione Fase 7)
  - Crea Document + DocumentVersion con il PDF generato
  - Risponde con il documento creato

Frontend:

ScanToPDFModal.tsx:
  - Titolo "Crea PDF da scansione"
  - Upload zone per più immagini (drag & drop multiplo)
  - Preview miniature delle immagini caricate
  - Riordina immagini (drag & drop per ordine pagine)
  - Toggle "Esegui OCR (estrai testo per ricerca)"
  - Campo "Titolo documento"
  - Select cartella
  - Select struttura metadati (opzionale)
  - Bottone "Crea PDF" → progress bar durante elaborazione
  - Feedback: "PDF creato con N pagine. Testo indicizzato per la ricerca."

Aggiorna FileExplorer.tsx:
  - Aggiungi bottone "Scansiona documento" accanto a "Carica documento"

TEST:
  - images_to_pdf con 3 immagini PNG → PDF con 3 pagine
  - ocr_image su immagine con testo → testo estratto correttamente
  - API scan_to_pdf: documento creato, DocumentIndex con testo OCR
  - Formato non supportato → 400 con lista formati supportati

Esegui: `pytest backend/apps/documents/tests/test_scanner.py -v`
```

---

## TEST INTEGRAZIONE FASE 9E

### Prompt per Cursor:

```
Test di integrazione Fase 9E.

1. `pytest backend/apps/protocols/tests/test_agid.py backend/apps/metadata/tests/test_templates.py backend/apps/documents/tests/test_scanner.py -v --cov`

2. `npm run test -- --run`

3. Test manuale conversione AGID:
   a) Crea protocollo con documento PDF allegato
   b) GET /api/protocols/{id}/stamped_document/ → scarica PDF con timbro
      → verifica: timbro visibile con numero protocollo, data, UO
   c) GET /api/protocols/{id}/coverpage/ → scarica copertina PDF
   d) Protocollo con documento DOCX allegato:
      → /stamped_document/ → converte in PDF via LibreOffice → applica timbro

4. Test template:
   a) Crea struttura metadati "Contratto" con campi: fornitore, valore, data_stipula
   b) Crea file DOCX con segnaposto:
      "Contratto con {{meta.fornitore}} del valore di €{{meta.valore}}"
      "Data: {{meta.data_stipula}} — Redatto da: {{user.full_name}}"
   c) Upload template su struttura "Contratto"
      → risponde con: segnaposto trovati
   d) Crea documento con struttura "Contratto", compila metadati
   e) GET /api/documents/{id}/fill_template/
      → scarica DOCX con valori reali al posto dei segnaposto

5. Test scanner:
   a) Prepara 2-3 immagini JPG con testo visibile
   b) POST /api/documents/scan_to_pdf/ con le immagini + perform_ocr=true
      → documento creato con PDF risultante
   c) GET /api/search/?q=testo_nell_immagine
      → documento trovato (indicizzato da OCR)
   d) Formato non supportato (es. .gif animata) → 400

6. Verifica LibreOffice nel container:
   `docker-compose exec backend libreoffice --version`
   → "LibreOffice X.Y.Z"

Crea `FASE_09E_TEST_REPORT.md`.
```
