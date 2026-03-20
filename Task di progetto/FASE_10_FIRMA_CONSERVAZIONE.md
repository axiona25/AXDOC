# AXDOC — FASE 10
# Firma Digitale e Conservazione

## Obiettivo
Implementare la firma digitale remota (CADES e PADES) con integrazione
verso provider esterni (es. Aruba) e il sistema di invio in conservazione
digitale con monitoraggio dello stato.

**Prerequisito: FASE 09 completata e tutti i test passanti.**
**Questa fase si inserisce tra la Fase 6 e la Fase 7.**

---

## CHECKLIST DI COMPLETAMENTO

- [ ] Modelli per richieste firma e conservazione
- [ ] Integrazione provider firma remota (RF-078) — Aruba o mock
- [ ] Supporto formato CADES (.p7m) (RF-076)
- [ ] Supporto formato PADES invisibile e grafico (RF-077)
- [ ] Firma singolo documento (RF-075)
- [ ] Firma da cartella (multipla) — menzione nei docs AXDOC
- [ ] Verifica OTP via SMS per firma avanzata (RF-078)
- [ ] Invio documento in conservazione (RF-079)
- [ ] Monitoraggio stato conservazione (RF-080)
- [ ] Storico firme per documento
- [ ] Integrazione nella struttura metadati (abilitazione firma per tipo doc)
- [ ] Frontend: panel firma documento
- [ ] Frontend: wizard OTP
- [ ] Frontend: stato conservazione nel panel documento
- [ ] Tutti i test passano (mock provider)

---

## STEP 6B.1 — Modelli: Firma e Conservazione

### Prompt per Cursor:

```
Crea `backend/apps/signatures/` per gestire firma digitale e conservazione.

Requisiti: RF-075..RF-080

Crea `backend/apps/signatures/models.py`:

------- FIRMA DIGITALE -------

SIGNATURE_FORMAT = [
  ('cades', 'CAdES (.p7m)'),       # RF-076
  ('pades_invisible', 'PAdES invisibile'),  # RF-077
  ('pades_graphic', 'PAdES grafica'),       # RF-077
]

SIGNATURE_STATUS = [
  ('pending_otp', 'In attesa OTP'),
  ('pending_provider', 'In elaborazione provider'),
  ('completed', 'Completata'),
  ('failed', 'Fallita'),
  ('expired', 'Scaduta'),
]

class SignatureRequest(models.Model):
  - id: UUID primary key
  - document: FK Document related_name='signature_requests'
  - document_version: FK DocumentVersion (versione da firmare)
  - requested_by: FK User
  - signer: FK User (chi deve firmare)
  - format: CharField choices SIGNATURE_FORMAT
  - status: CharField choices SIGNATURE_STATUS default 'pending_otp'
  
  # Dati provider
  - provider: CharField default='aruba' (nome provider esterno)
  - provider_request_id: CharField blank=True (ID restituito dal provider)
  - provider_response: JSONField default=dict (risposta raw del provider)
  
  # OTP (RF-078)
  - otp_sent_at: DateTimeField null=True
  - otp_expires_at: DateTimeField null=True (scadenza OTP, default +10min)
  - otp_verified: bool default False
  - otp_attempts: IntegerField default 0
  
  # File firmato
  - signed_file: FileField upload_to='signed/%Y/%m/' null=True
  - signed_file_name: CharField blank=True
  - signed_at: DateTimeField null=True
  
  # Metadati firma
  - signature_reason: CharField blank=True (motivo della firma)
  - signature_location: CharField blank=True (luogo firma, per PADES grafica)
  - graphic_signature_image: ImageField upload_to='sig_images/' null=True
    (immagine firma grafica per PADES grafica)
  
  - created_at: auto_now_add
  - updated_at: auto_now
  - error_message: TextField blank=True

------- CONSERVAZIONE DIGITALE -------

CONSERVATION_STATUS = [
  ('draft', 'Da inviare'),
  ('pending', 'In attesa invio'),
  ('sent', 'Inviato al provider'),
  ('in_progress', 'In elaborazione'),
  ('completed', 'Conservato'),
  ('failed', 'Fallito'),
  ('rejected', 'Rifiutato dal provider'),
]

class ConservationRequest(models.Model):
  - id: UUID primary key
  - document: FK Document related_name='conservation_requests'
  - document_version: FK DocumentVersion (versione da conservare)
  - protocol: FK Protocol null=True (protocollo associato, se presente)
  - requested_by: FK User
  
  # Provider
  - provider: CharField default='aruba'
  - provider_request_id: CharField blank=True
  - provider_package_id: CharField blank=True (ID pacchetto conservazione)
  - provider_response: JSONField default=dict
  
  # Stato (RF-080)
  - status: CharField choices CONSERVATION_STATUS default='draft'
  - submitted_at: DateTimeField null=True
  - completed_at: DateTimeField null=True
  - last_checked_at: DateTimeField null=True
  
  # Metadati obbligatori conservazione AGID
  - document_type: CharField (tipologia documento secondo AGID)
  - document_date: DateField (data del documento)
  - reference_number: CharField blank=True (numero protocollo o riferimento)
  - conservation_class: CharField default='1' 
    (classe conservazione: 1=10anni, 2=30anni, 3=permanente)
  
  - created_at: auto_now_add
  - updated_at: auto_now
  - error_message: TextField blank=True
  - certificate_url: CharField blank=True (URL attestato conservazione)

Crea migration: `python manage.py makemigrations signatures`
```

---

## STEP 6B.2 — Provider Abstraction Layer

### Prompt per Cursor:

```
Crea il layer di astrazione per i provider di firma e conservazione.
Questo permette di usare Aruba in produzione e un mock in sviluppo/test.

Crea `backend/apps/signatures/providers/`:

`backend/apps/signatures/providers/base.py`:

class BaseSignatureProvider(ABC):
  
  @abstractmethod
  def request_signature(
    self,
    document_path: str,
    signer_phone: str,
    format: str,
    reason: str = '',
    location: str = '',
    graphic_image_path: str = None,
  ) -> dict:
    """
    Invia documento al provider per firma e manda OTP all'utente.
    Ritorna: {
      "provider_request_id": str,
      "otp_expires_at": datetime,
      "message": str
    }
    """
    pass
  
  @abstractmethod
  def confirm_signature(
    self,
    provider_request_id: str,
    otp_code: str,
  ) -> dict:
    """
    Conferma firma con OTP inserito dall'utente.
    Ritorna: {
      "success": bool,
      "signed_file_base64": str | None,  # file firmato in base64
      "error": str | None
    }
    """
    pass
  
  @abstractmethod
  def verify_signature(self, signed_file_path: str) -> dict:
    """
    Verifica validità di un file firmato.
    Ritorna: {
      "valid": bool,
      "signer_name": str,
      "signed_at": datetime,
      "certificate_info": dict
    }
    """
    pass

class BaseConservationProvider(ABC):
  
  @abstractmethod
  def submit_for_conservation(
    self,
    document_path: str,
    metadata: dict,
  ) -> dict:
    """
    Invia documento in conservazione.
    metadata include: document_type, document_date, reference_number, ecc.
    Ritorna: {
      "provider_request_id": str,
      "provider_package_id": str,
      "status": str
    }
    """
    pass
  
  @abstractmethod
  def check_conservation_status(self, provider_request_id: str) -> dict:
    """
    Controlla lo stato di una richiesta di conservazione.
    Ritorna: {
      "status": str,  # pending|in_progress|completed|failed|rejected
      "message": str,
      "certificate_url": str | None
    }
    """
    pass

---

`backend/apps/signatures/providers/mock_provider.py`:

class MockSignatureProvider(BaseSignatureProvider):
  """
  Provider mock per sviluppo e test.
  Simula il comportamento di Aruba senza chiamate reali.
  OTP fisso: "123456"
  """
  
  def request_signature(self, document_path, signer_phone, format, **kwargs):
    # Simula invio OTP (logga in console)
    logger.info(f"[MOCK] OTP inviato a {signer_phone}: 123456")
    return {
      "provider_request_id": f"MOCK-{uuid4()}",
      "otp_expires_at": datetime.now() + timedelta(minutes=10),
      "message": f"OTP inviato a {signer_phone[-4:].rjust(10, '*')}"
    }
  
  def confirm_signature(self, provider_request_id, otp_code):
    if otp_code != "123456":
      return {"success": False, "signed_file_base64": None, "error": "OTP non valido"}
    
    # Ritorna il file originale come "firmato" (senza firma reale)
    # In produzione qui ci sarebbe il file firmato dal provider
    mock_signed_content = b"MOCK_SIGNED_FILE_CONTENT"
    return {
      "success": True,
      "signed_file_base64": base64.b64encode(mock_signed_content).decode(),
      "error": None
    }
  
  def verify_signature(self, signed_file_path):
    return {
      "valid": True,
      "signer_name": "Mock Signer",
      "signed_at": datetime.now(),
      "certificate_info": {"issuer": "Mock CA", "serial": "12345"}
    }

class MockConservationProvider(BaseConservationProvider):
  """
  Provider mock per conservazione.
  Simula l'invio e dopo 5 secondi segna come completato.
  """
  
  def submit_for_conservation(self, document_path, metadata):
    logger.info(f"[MOCK] Documento inviato in conservazione: {document_path}")
    return {
      "provider_request_id": f"CONS-MOCK-{uuid4()}",
      "provider_package_id": f"PKG-{uuid4()}",
      "status": "pending"
    }
  
  def check_conservation_status(self, provider_request_id):
    # Mock: dopo la prima verifica segna come completato
    return {
      "status": "completed",
      "message": "Documento conservato con successo (MOCK)",
      "certificate_url": f"https://mock-conservation.example.com/cert/{provider_request_id}"
    }

---

`backend/apps/signatures/providers/aruba_provider.py`:

class ArubaSignatureProvider(BaseSignatureProvider):
  """
  Integrazione reale con Aruba Sign.
  Le credenziali vengono da settings: ARUBA_API_URL, ARUBA_API_KEY, ecc.
  
  NOTA: Questo è uno stub strutturato. L'implementazione reale
  richiede contratto e credenziali Aruba.
  """
  
  def __init__(self):
    self.api_url = settings.ARUBA_SIGN_API_URL
    self.api_key = settings.ARUBA_SIGN_API_KEY
    self.user_id = settings.ARUBA_SIGN_USER_ID
  
  def request_signature(self, document_path, signer_phone, format, **kwargs):
    # TODO: implementare chiamata reale API Aruba RemoteSign
    # Documentazione: https://doc.aruba.it/remotesign/
    raise NotImplementedError(
      "Implementare chiamata API Aruba. "
      "Usa ARUBA_SIGN_API_URL e ARUBA_SIGN_API_KEY da settings."
    )
  
  def confirm_signature(self, provider_request_id, otp_code):
    raise NotImplementedError("Implementare conferma firma Aruba")
  
  def verify_signature(self, signed_file_path):
    raise NotImplementedError("Implementare verifica firma Aruba")

class ArubaConservationProvider(BaseConservationProvider):
  """
  Integrazione reale con Aruba Conservazione.
  NOTA: Stub strutturato. Richiede contratto Aruba.
  """
  
  def __init__(self):
    self.api_url = settings.ARUBA_CONSERVATION_API_URL
    self.api_key = settings.ARUBA_CONSERVATION_API_KEY
  
  def submit_for_conservation(self, document_path, metadata):
    raise NotImplementedError(
      "Implementare invio ad Aruba Conservazione. "
      "Documentazione: https://doc.aruba.it/conservazione/"
    )
  
  def check_conservation_status(self, provider_request_id):
    raise NotImplementedError("Implementare check stato Aruba Conservazione")

---

`backend/apps/signatures/providers/factory.py`:

def get_signature_provider() -> BaseSignatureProvider:
  provider_name = settings.SIGNATURE_PROVIDER  # 'mock' o 'aruba'
  if provider_name == 'aruba':
    return ArubaSignatureProvider()
  return MockSignatureProvider()  # default in sviluppo

def get_conservation_provider() -> BaseConservationProvider:
  provider_name = settings.CONSERVATION_PROVIDER
  if provider_name == 'aruba':
    return ArubaConservationProvider()
  return MockConservationProvider()

---

Aggiungi in `backend/config/settings/base.py`:
  SIGNATURE_PROVIDER = env('SIGNATURE_PROVIDER', default='mock')
  CONSERVATION_PROVIDER = env('CONSERVATION_PROVIDER', default='mock')
  ARUBA_SIGN_API_URL = env('ARUBA_SIGN_API_URL', default='')
  ARUBA_SIGN_API_KEY = env('ARUBA_SIGN_API_KEY', default='')
  ARUBA_SIGN_USER_ID = env('ARUBA_SIGN_USER_ID', default='')
  ARUBA_CONSERVATION_API_URL = env('ARUBA_CONSERVATION_API_URL', default='')
  ARUBA_CONSERVATION_API_KEY = env('ARUBA_CONSERVATION_API_KEY', default='')

Aggiungi in `backend/.env.example`:
  SIGNATURE_PROVIDER=mock
  CONSERVATION_PROVIDER=mock
  # Per produzione Aruba:
  # SIGNATURE_PROVIDER=aruba
  # ARUBA_SIGN_API_URL=https://...
  # ARUBA_SIGN_API_KEY=...
  # ARUBA_SIGN_USER_ID=...
  # CONSERVATION_PROVIDER=aruba
  # ARUBA_CONSERVATION_API_URL=https://...
  # ARUBA_CONSERVATION_API_KEY=...
```

---

## STEP 6B.3 — API Firma Digitale

### Prompt per Cursor:

```
Crea le API per la firma digitale in `backend/apps/signatures/views.py`.

Requisiti: RF-075, RF-076, RF-077, RF-078

------- FIRMA -------

SignatureRequestViewSet:

POST /api/documents/{doc_id}/request_signature/:
  Avvia richiesta firma (RF-075, RF-078)
  - Solo utenti con can_write O ADMIN O l'approvatore nel workflow corrente
  - Corpo:
    {
      "signer_id": "uuid",       # chi deve firmare
      "format": "cades|pades_invisible|pades_graphic",
      "reason": "Approvazione contratto",
      "location": "Milano",      # opzionale, per PADES grafica
      "graphic_signature": "base64_image"  # opzionale, per PADES grafica
    }
  - Valida: il documento deve essere in stato APPROVED (logica aziendale)
  - Chiama get_signature_provider().request_signature(...)
  - Crea SignatureRequest con status='pending_otp'
  - Invia Notification al signer: "Hai un documento da firmare"
  - Risponde: { "signature_request_id": "...", "otp_message": "OTP inviato a ***1234" }

POST /api/signatures/{sig_id}/verify_otp/:
  Verifica OTP e completa firma (RF-078)
  - Solo il signer della richiesta
  - Corpo: { "otp_code": "123456" }
  - Verifica: status='pending_otp', otp non scaduto (otp_expires_at > now)
  - Se otp_attempts >= 3: status='failed', risponde 400
  - Incrementa otp_attempts
  - Chiama provider.confirm_signature(provider_request_id, otp_code)
  - Se successo:
    * Salva file firmato (decodifica base64, salva su FileField)
    * Imposta status='completed', signed_at=now()
    * Crea nuova DocumentVersion con il file firmato
      (version_number+1, change_description="Documento firmato digitalmente")
    * Aggiorna Document.status se opportuno
    * Crea AuditLog: action='document_signed'
    * Invia Notification al requested_by: "Documento firmato da [signer]"
  - Se fallisce: status='failed', error_message dal provider
  - Risponde: { "success": bool, "message": str }

POST /api/signatures/{sig_id}/resend_otp/:
  Reinvia OTP (utente non ha ricevuto SMS)
  - Solo il signer, solo se status='pending_otp' e non scaduto
  - Chiama nuovamente request_signature sul provider
  - Azzera otp_attempts, aggiorna otp_expires_at
  - Max 3 reinvii totali

GET /api/documents/{doc_id}/signatures/:
  Storico firme del documento
  - Lista SignatureRequest con: signer, formato, stato, data firma
  - Accessibile a chi ha can_read

GET /api/signatures/{sig_id}/verify/:
  Verifica validità firma (RF-075)
  - Chiama provider.verify_signature(signed_file_path)
  - Risponde con: valid, signer_name, signed_at, certificate_info

------- FIRMA DA CARTELLA (multi-documento) -------

POST /api/folders/{folder_id}/request_signature/:
  Firma multipla tutti i documenti approvati in una cartella
  - Corpo: { "signer_id": "...", "format": "...", "reason": "..." }
  - Crea una SignatureRequest per ogni documento APPROVED nella cartella
  - Il signer riceve una sola notifica con count documenti
  - Risponde: { "signature_requests": [id1, id2, ...], "count": N }

Crea `backend/apps/signatures/serializers.py`:
  - SignatureRequestSerializer
  - SignatureRequestDetailSerializer (con info documento e signer)
  - OTPVerifySerializer: otp_code (6 cifre, validazione regex)
  - RequestSignatureSerializer: signer_id, format, reason, location

Crea `backend/apps/signatures/urls.py` e aggiungi a config/urls.py

TEST `backend/apps/signatures/tests/test_signature.py`:
  - Richiesta firma: SignatureRequest creata, status=pending_otp
  - OTP corretto (123456 con mock): file firmato salvato, nuova versione documento
  - OTP sbagliato: otp_attempts incrementato
  - OTP sbagliato 3 volte: status=failed
  - OTP scaduto (simula otp_expires_at nel passato): 400
  - Firma da cartella: crea SignatureRequest per ogni doc approvato
  - Verifica firma: risponde con dati mock

Esegui: `pytest backend/apps/signatures/tests/test_signature.py -v --tb=short`
Tutti i test devono passare con SIGNATURE_PROVIDER=mock
```

---

## STEP 6B.4 — API Conservazione Digitale

### Prompt per Cursor:

```
Crea le API per la conservazione digitale in `backend/apps/signatures/views.py`.

Requisiti: RF-079, RF-080

------- CONSERVAZIONE -------

ConservationRequestViewSet:

POST /api/documents/{doc_id}/send_to_conservation/:
  Invia documento in conservazione (RF-079)
  - Solo ADMIN o APPROVER
  - Prerequisiti (validati con 400 se non rispettati):
    * Documento in stato APPROVED
    * Almeno una firma completata (SignatureRequest.status='completed')
    * Nessuna richiesta di conservazione già in stato sent/in_progress/completed
  - Corpo:
    {
      "document_type": "Contratto",      # tipologia AGID
      "document_date": "2024-03-10",     # data del documento
      "reference_number": "2024/IT/0042", # numero protocollo (opzionale)
      "conservation_class": "1"           # 1=10anni, 2=30anni, 3=permanente
    }
  - Chiama get_conservation_provider().submit_for_conservation(...)
  - Crea ConservationRequest con status='sent'
  - Crea AuditLog: action='document_sent_to_conservation'
  - Invia Notification al requested_by: "Documento inviato in conservazione"
  - Risponde: { "conservation_request_id": "...", "status": "sent" }

POST /api/conservation/{cons_id}/check_status/:
  Controlla aggiornamento stato conservazione (RF-080)
  - Solo chi ha inviato O ADMIN
  - Chiama provider.check_conservation_status(provider_request_id)
  - Aggiorna ConservationRequest:
    * status dal provider
    * last_checked_at = now()
    * Se completed: completed_at = now(), certificate_url dal provider
    * Se failed/rejected: error_message dal provider
  - Risponde con stato aggiornato

GET /api/documents/{doc_id}/conservation/:
  Stato conservazione del documento (RF-080)
  - Lista ConservationRequest con stato, date, certificate_url
  - Per tutti con can_read

GET /api/conservation/:
  Lista tutte le richieste di conservazione (solo ADMIN)
  - Filtrabile per status, provider, date range
  - Utile per monitoraggio centrale (RF-080)

POST /api/conservation/check_all_pending/:
  Aggiorna lo stato di tutte le richieste in_progress
  Solo ADMIN — da chiamare periodicamente (o via management command)
  - Chiama check_conservation_status su tutte le ConservationRequest
    con status in ['sent', 'in_progress']
  - Risponde con { "checked": N, "updated": N, "completed": N, "failed": N }

Crea management command `backend/apps/signatures/management/commands/check_conservation_status.py`:
  - Chiama ConservationService.check_all_pending()
  - Uso: `python manage.py check_conservation_status`
  - Da schedulare (cron o celery beat) ogni ora in produzione

Crea `backend/apps/signatures/services.py`:

ConservationService:
  - submit(document, user, metadata): logica completa invio
  - check_status(conservation_request): logica aggiornamento singolo
  - check_all_pending(): aggiorna tutti i pending
  - get_document_conservation_status(document): stato complessivo

SignatureService:
  - request(document, signer, format, reason, location, graphic): logica firma
  - verify_otp(signature_request, otp_code): verifica e completa
  - get_document_signature_status(document): stato firme del documento

TEST `backend/apps/signatures/tests/test_conservation.py`:
  - Invio conservazione: ConservationRequest creata, status='sent'
  - Prerequisito firma mancante → 400 con messaggio chiaro
  - Documento non approved → 400
  - check_status: aggiorna status da provider mock → 'completed'
  - check_status: certificate_url salvato quando completed
  - check_all_pending: aggiorna tutte le richieste pending
  - ADMIN vede lista tutte le richieste
  - Non-admin non può vedere lista globale

Esegui: `pytest backend/apps/signatures/ -v --tb=short`
Coverage deve essere > 80% con mock provider.
```

---

## STEP 6B.5 — Integrazione con Strutture Metadati

### Prompt per Cursor:

```
Integra la firma digitale con le strutture metadati (preparata in Fase 4).

Requisiti: AXDOC.docx — "abilitare la firma digitale remota selezionando
anche i possibili firmatari" nella struttura metadati.

Modifica `backend/apps/metadata/models.py`:

Aggiungi in MetadataStructure:
  - signature_enabled: bool default False
    (se True, i documenti di questo tipo possono essere firmati)
  - allowed_signers: ManyToMany User
    (utenti abilitati come firmatari per questa struttura — vuoto = tutti gli APPROVER)
  - signature_format: CharField choices SIGNATURE_FORMAT default='pades_invisible'
    (formato di firma predefinito per questa struttura)
  - conservation_enabled: bool default False
    (se True, supporta invio in conservazione)
  - conservation_class: CharField default='1'
    (classe conservazione predefinita)
  - conservation_document_type: CharField blank=True
    (tipo documento AGID predefinito)

Crea migration: `python manage.py makemigrations metadata`

Modifica SignatureRequestViewSet:
  In POST /api/documents/{doc_id}/request_signature/:
  - Se documento ha metadata_structure con signature_enabled=False → 400
    "La struttura metadati di questo documento non consente la firma"
  - Se allowed_signers non vuoto e il signer non è nella lista → 400
    "L'utente selezionato non è un firmatario autorizzato per questo tipo di documento"
  - Usa signature_format della struttura come default se non specificato

Modifica ConservationRequestViewSet:
  In POST /api/documents/{doc_id}/send_to_conservation/:
  - Se documento ha metadata_structure con conservation_enabled=False → 400
  - Usa conservation_class e conservation_document_type come default

Modifica MetadataStructureSerializer (Fase 4):
  Aggiungi campi: signature_enabled, allowed_signers, signature_format,
  conservation_enabled, conservation_class, conservation_document_type

TEST:
  - Documento con struttura firma disabilitata → 400 su request_signature
  - Documento con struttura firma abilitata, firmatario non autorizzato → 400
  - Documento con struttura firma abilitata, firmatario autorizzato → OK

Esegui: `pytest backend/apps/signatures/ backend/apps/metadata/ -v`
```

---

## STEP 6B.6 — Frontend: Firma e Conservazione

### Prompt per Cursor:

```
Crea i componenti frontend per firma digitale e conservazione.

Aggiungi `frontend/src/services/signatureService.ts`:
  - requestSignature(docId, data): POST request firma
  - verifyOtp(sigId, otp): POST verifica OTP
  - resendOtp(sigId): POST reinvio OTP
  - getDocumentSignatures(docId): GET storico firme
  - verifySignatureValidity(sigId): GET verifica validità
  - sendToConservation(docId, data): POST invio conservazione
  - checkConservationStatus(consId): POST check stato
  - getDocumentConservation(docId): GET stato conservazione documento

Aggiungi `frontend/src/types/signatures.ts`:
  - SignatureFormat (enum: cades, pades_invisible, pades_graphic)
  - SignatureStatus (enum)
  - SignatureRequest, ConservationRequest (types completi)
  - RequestSignatureForm, VerifyOTPForm, SendToConservationForm

Crea `frontend/src/components/signatures/`:

RequestSignatureModal.tsx:
  Wizard a 3 step per richiedere la firma:
  
  Step 1 — Configurazione firma:
    - Select "Firmatario" (lista utenti autorizzati, filtrata da metadata_structure)
    - Select "Formato firma":
      * CAdES (.p7m) — con tooltip "Firma il file in un file .p7m esterno"
      * PAdES invisibile — "Firma incorporata nel PDF, non visibile"
      * PAdES grafica — "Firma incorporata nel PDF con immagine grafica"
    - Se PAdES grafica: upload immagine firma (preview)
    - Campo "Motivo firma" (es. "Approvazione contratto")
    - Campo "Luogo" (solo se PAdES)
    - Bottone "Invia OTP al firmatario"
  
  Step 2 — Conferma invio OTP:
    - Messaggio "OTP inviato al numero ***1234 del firmatario [Nome]"
    - Info: "Il firmatario deve inserire il codice ricevuto via SMS"
    - Bottone "Attendi conferma" (chiude e aspetta)
    - Link "Invia come firmatario (sono io)" se l'utente loggato è il signer
    → Se il signer è l'utente corrente: apre direttamente Step 3

  Step 3 — Inserimento OTP (visibile solo se signer = current user):
    - 6 input separati per le cifre OTP (stile autenticazione bancaria)
    - Timer countdown scadenza (10 minuti)
    - Link "Non hai ricevuto l'OTP? Reinvia"
    - Bottone "Firma Documento"
    - Loading state durante firma
    - Successo: "Documento firmato con successo ✓"

OTPInputModal.tsx:
  Modal separato per il firmatario che apre dalla notifica
  - Recupera SignatureRequest dall'ID in notifica
  - Mostra documento da firmare (titolo, versione)
  - 6 input OTP con auto-focus e paste support
  - Timer countdown
  - Bottone "Firma" → verifyOtp → feedback successo/errore

SignatureHistoryPanel.tsx:
  Panel o sezione nel DocumentDetailPanel:
  - Lista firme completate: firmatario, formato, data, "Verifica validità"
  - Lista firme pendenti: firmatario, formato, "In attesa OTP", scadenza
  - Lista firme fallite: motivo errore
  - Bottone "Richiedi Firma" (se utente ha permesso e struttura abilitata)

ConservationPanel.tsx:
  - Se nessuna richiesta: 
    * Info "Prerequisiti: documento Approvato + almeno una Firma"
    * Bottone "Invia in Conservazione" (disabilitato se prerequisiti mancanti, con tooltip)
  - Form inline:
    * Tipo documento (text, pre-compilato da metadata_structure se disponibile)
    * Data documento (date picker)
    * Numero riferimento (pre-compilato da protocollo se presente)
    * Classe conservazione (select: 10 anni / 30 anni / Permanente)
  - Se richiesta esistente:
    * Badge stato: In attesa / In elaborazione / Conservato / Fallito
    * Data invio, data completamento
    * Bottone "Verifica stato" (chiama check_status)
    * Se completato: link "Scarica attestato di conservazione"
    * Se fallito: messaggio errore + bottone "Riprova"

ConservationStatusBadge.tsx:
  - Mini badge riutilizzabile: colore per stato
    * draft=grigio, sent=blu, in_progress=arancio, 
      completed=verde, failed=rosso, rejected=rosso scuro

Aggiorna `DocumentDetailPanel.tsx` (da Fase 3):
  - Aggiungi Tab "Firma" con SignatureHistoryPanel
  - Aggiungi Tab "Conservazione" con ConservationPanel
  - Mostra badge ConservationStatusBadge accanto allo stato documento
    se esiste una richiesta di conservazione

Aggiorna MetadataStructureForm.tsx (da Fase 4):
  Aggiungi sezione "Firma e Conservazione":
  - Toggle "Abilita firma digitale"
    → Se abilitato: select firmatari autorizzati, select formato default
  - Toggle "Abilita conservazione digitale"
    → Se abilitato: select classe conservazione default, campo tipo documento AGID

TEST Vitest:
  - RequestSignatureModal: render step 1, navigazione step, submit
  - OTPInputModal: 6 input, paste, submit, timer countdown
  - SignatureHistoryPanel: render stati diversi (pending, completed, failed)
  - ConservationPanel: bottone disabilitato senza prerequisiti
  - ConservationPanel: form submit, aggiornamento stato dopo check

Esegui: `npm run test -- --run`
Esegui: `npm run build` → nessun errore TypeScript
```

---

## TEST INTEGRAZIONE FASE 6B

### Prompt per Cursor:

```
Esegui i test di integrazione completi per la Fase 6B.

1. Backend tests:
   `docker-compose exec backend pytest apps/signatures/ apps/metadata/ -v --cov=apps/signatures`
   → Coverage > 80%, tutti i test passano con SIGNATURE_PROVIDER=mock

2. Frontend tests:
   `docker-compose exec frontend npm run test -- --run`
   → Tutti i test passano

3. Test manuale — ciclo completo firma e conservazione:

   Setup (riutilizza dati Fasi precedenti):
   - Documento approvato tramite workflow (stato APPROVED)
   - Struttura metadati "Contratto" con signature_enabled=True,
     allowed_signers=[approvatore], conservation_enabled=True
   
   FIRMA:
   a) Come admin, apri DocumentDetailPanel → tab "Firma"
      → Bottone "Richiedi Firma" visibile e attivo
   b) Apri RequestSignatureModal:
      - Seleziona firmatario: approvatore@test.com
      - Formato: PAdES invisibile
      - Motivo: "Approvazione documento"
      - Click "Invia OTP" → status=pending_otp
   c) Nel log Django console: "[MOCK] OTP inviato a ***1234: 123456"
   d) Apri OTPInputModal (o usa il wizard se signer=current user):
      - Inserisci OTP: 123456 → firma completata
      - Nuova versione documento creata con file firmato
   e) Verifica: GET /api/documents/{id}/signatures/ → firma in lista con status=completed
   f) Click "Verifica validità" → risponde con dati mock validi
   
   Firma fallita (test errore):
   g) Richiedi nuova firma
   h) Inserisci OTP sbagliato 3 volte → status=failed, messaggio errore
   
   CONSERVAZIONE:
   i) Con firma completata: tab "Conservazione" → bottone attivo
   j) Compila form: tipo="Contratto", data=oggi, classe=1 (10 anni)
   k) Click "Invia in Conservazione" → status=sent
   l) Click "Verifica stato" → mock risponde completed, certificate_url presente
   m) Link "Scarica attestato" → naviga all'URL mock
   
   Prerequisiti mancanti:
   n) Documento in stato DRAFT → bottone conservazione disabilitato con tooltip
   o) Documento APPROVED ma senza firma → conservazione disabilitata con tooltip
   
   Struttura metadati:
   p) Crea struttura "Ricevuta" con signature_enabled=False
   q) Documento con struttura "Ricevuta" → richiesta firma → 400

4. Verifica AuditLog:
   GET /api/audit/?action=document_signed → entries per le firme eseguite
   GET /api/audit/?action=document_sent_to_conservation → entries conservazione

5. Management command:
   `docker-compose exec backend python manage.py check_conservation_status`
   → Output: "Checked: N, Updated: N, Completed: N, Failed: 0"

Se tutti i test passano, procedi con la FASE 7.
Crea `FASE_06B_TEST_REPORT.md` con i risultati.
```
