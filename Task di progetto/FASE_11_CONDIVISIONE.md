# AXDOC — FASE 11
# Condivisione Documenti con Utenti Interni ed Esterni

## Fonte nei documenti di analisi
AXDOC.docx — sezione "Condivisione":
> "È possibile condividere un documento o un protocollo, sia con un collega 
> presente all'interno degli utenti registrati sia con utenti esterni, 
> attraverso l'invio di un link tramite email."

Documento Collaudo — segnalazioni aggiuntive:
> "Permessi di visualizzazione dei documenti"

**Questa funzionalità NON è presente in nessuna fase precedente.**

**Prerequisito: FASE 05 completata e tutti i test passanti.**

---

## CHECKLIST DI COMPLETAMENTO

- [ ] Condivisione documento con utente interno (per email o username)
- [ ] Condivisione documento con utente esterno (link temporaneo via email)
- [ ] Condivisione protocollo con utente interno/esterno
- [ ] Link di condivisione con scadenza configurabile
- [ ] Accesso link pubblico senza login (sola lettura + download)
- [ ] Revoca condivisione
- [ ] Lista condivisioni attive per documento
- [ ] Notifica al destinatario interno (usa sistema notifiche Fase 7)
- [ ] Email al destinatario esterno con link
- [ ] AuditLog: accesso tramite link condivisione
- [ ] Frontend: modal condivisione con copy link
- [ ] Frontend: pagina pubblica accesso documento condiviso
- [ ] Tutti i test passano

---

## STEP 9A.1 — Modelli Condivisione

### Prompt per Cursor:

```
Crea `backend/apps/sharing/` per la condivisione documenti e protocolli.

Fonte: AXDOC.docx sezione "Condivisione"

Crea `backend/apps/sharing/models.py`:

SHARE_TARGET_TYPE = [
  ('document', 'Documento'),
  ('protocol', 'Protocollo'),
]

SHARE_RECIPIENT_TYPE = [
  ('internal', 'Utente interno'),
  ('external', 'Utente esterno'),
]

class ShareLink(models.Model):
  - id: UUID primary key
  - token: CharField unique (UUID generato, usato nell'URL pubblico)
  - target_type: CharField choices SHARE_TARGET_TYPE
  - document: FK Document null=True related_name='share_links'
  - protocol: FK Protocol null=True related_name='share_links'
  - shared_by: FK User
  - recipient_type: CharField choices SHARE_RECIPIENT_TYPE
  
  # Per utenti interni
  - recipient_user: FK User null=True related_name='received_shares'
  
  # Per utenti esterni
  - recipient_email: EmailField blank=True
  - recipient_name: CharField blank=True (nome visualizzato nell'email)
  
  # Controllo accesso
  - can_download: bool default True
  - password_protected: bool default False
  - access_password: CharField blank=True (hash bcrypt se password_protected)
  
  # Scadenza
  - expires_at: DateTimeField null=True (null = nessuna scadenza)
  - max_accesses: IntegerField null=True (null = illimitato)
  - access_count: IntegerField default 0
  
  # Stato
  - is_active: bool default True
  - created_at: auto_now_add
  - last_accessed_at: DateTimeField null=True
  
  Metodo: is_valid() → bool
    Controlla: is_active, not expired, not max_accesses exceeded
  
  Metodo: get_absolute_url() → str
    Ritorna: f"/share/{token}"

class ShareAccessLog(models.Model):
  """Log ogni accesso al link pubblico"""
  - share_link: FK ShareLink
  - accessed_at: auto_now_add
  - ip_address: GenericIPAddressField null=True
  - user_agent: TextField blank=True
  - action: CharField choices [('view', 'Visualizzazione'), ('download', 'Download')]

Crea migration: `python manage.py makemigrations sharing`
```

---

## STEP 9A.2 — API Condivisione

### Prompt per Cursor:

```
Crea le API per la condivisione in `backend/apps/sharing/views.py`.

ShareLinkViewSet:

POST /api/documents/{doc_id}/share/:
  Crea link di condivisione per documento
  - Richiede autenticazione + can_read sul documento
  - Corpo:
    {
      "recipient_type": "internal|external",
      "recipient_user_id": "uuid",       # se internal
      "recipient_email": "x@ext.com",    # se external
      "recipient_name": "Mario Bianchi", # se external
      "can_download": true,
      "expires_in_days": 7,              # null = nessuna scadenza
      "max_accesses": null,
      "password": null                   # opzionale
    }
  - Crea ShareLink con token UUID
  - Se internal:
    * Aggiunge recipient_user a DocumentPermission (can_read=True)
    * Invia Notification con link_url=/documents/{id}
    * Crea AuditLog action='document_shared'
  - Se external:
    * Invia email con link: {FRONTEND_URL}/share/{token}
    * Email include: nome documento, chi condivide, scadenza, bottone accesso
    * Crea AuditLog action='document_shared_external'
  - Risponde: { "share_link_id": "...", "token": "...", "url": "..." }

POST /api/protocols/{proto_id}/share/:
  Come sopra ma per protocollo
  - Verifica che l'utente abbia accesso al protocollo

GET /api/documents/{doc_id}/shares/:
  Lista condivisioni attive del documento
  - Solo chi ha can_write O ADMIN
  - Include: recipient (user o email), tipo, scadenza, accessi, stato

GET /api/protocols/{proto_id}/shares/:
  Lista condivisioni attive del protocollo

DELETE /api/sharing/{share_id}/revoke/:
  Revoca condivisione (is_active = False)
  - Solo shared_by O ADMIN
  - Se internal: rimuove da DocumentPermission

GET /api/sharing/my_shared/:
  Documenti che l'utente ha condiviso (shared_by = current_user)
  - Paginato, con stato attivo/scaduto

--- ACCESSO PUBBLICO (no autenticazione) ---

GET /api/public/share/{token}/:
  Accesso pubblico al link condiviso (senza JWT)
  - Verifica ShareLink.is_valid()
  - Se password_protected: 
    → risponde 401 con {"requires_password": true}
  - Incrementa access_count, aggiorna last_accessed_at
  - Crea ShareAccessLog
  - Risponde con:
    {
      "document": { titolo, descrizione, stato, versione_corrente },
      "shared_by": { nome, email },
      "can_download": bool,
      "expires_at": datetime | null,
      "accesses_remaining": int | null
    }

POST /api/public/share/{token}/verify_password/:
  Verifica password per link protetto
  - Corpo: { "password": "..." }
  - Verifica hash, risponde: { "valid": true } + session token temporaneo

GET /api/public/share/{token}/download/:
  Download del documento/protocollo via link pubblico
  - Verifica is_valid() + can_download=True
  - Verifica password se richiesta
  - Crea ShareAccessLog con action='download'
  - Serve il file con FileResponse

Crea `backend/apps/sharing/serializers.py`:
  - ShareLinkSerializer
  - ShareLinkCreateSerializer
  - PublicShareSerializer (solo dati non sensibili)
  - ShareAccessLogSerializer

Crea `backend/apps/sharing/emails.py`:
  send_share_email(share_link):
    Invia email HTML all'utente esterno con:
    - Oggetto: "{shared_by.name} ha condiviso un documento con te"
    - Corpo: descrizione documento, info scadenza, bottone "Accedi al documento"
    - Link: {FRONTEND_URL}/share/{token}
    - Footer: "Questo link scade il {expires_at}" O "Questo link non scade"

Crea `backend/apps/sharing/urls.py` e aggiungi a config/urls.py
  - /api/documents/{id}/share/
  - /api/protocols/{id}/share/  
  - /api/sharing/
  - /api/public/share/{token}/  (no autenticazione)

TEST `backend/apps/sharing/tests/`:
  - Condivisione interna: DocumentPermission creata, notifica inviata
  - Condivisione esterna: ShareLink creata con token, email inviata (mock)
  - Accesso link valido: incrementa access_count
  - Accesso link scaduto: 410 Gone
  - Accesso link max_accesses raggiunto: 410 Gone
  - Accesso link revocato: 410 Gone
  - Download senza can_download: 403
  - Password sbagliata: 401

Esegui: `pytest backend/apps/sharing/ -v --tb=short`
```

---

## STEP 9A.3 — Frontend: Condivisione

### Prompt per Cursor:

```
Crea i componenti frontend per la condivisione.

Aggiungi `frontend/src/services/sharingService.ts`:
  - shareDocument(docId, data): POST condivisione documento
  - shareProtocol(protoId, data): POST condivisione protocollo
  - getDocumentShares(docId): GET lista condivisioni
  - revokeShare(shareId): DELETE revoca
  - getPublicShare(token): GET accesso pubblico
  - verifySharePassword(token, password): POST verifica password
  - downloadSharedFile(token): GET download pubblico

Crea `frontend/src/components/sharing/`:

ShareModal.tsx:
  Modal per creare una condivisione. Campi:
  - Toggle: "Utente interno" / "Utente esterno"
  - Se interno: select utente dalla lista (searchable, autocomplete)
  - Se esterno: input email + input nome destinatario
  - Toggle "Permetti download"
  - Select "Scadenza": Nessuna / 1 giorno / 7 giorni / 30 giorni / Personalizzata
    → Se personalizzata: date picker
  - Toggle "Proteggi con password" → input password
  - Bottone "Condividi"
  - Dopo creazione: mostra link con bottone "Copia link" (clipboard API)
    e QR code (opzionale, usa libreria qrcode)

ShareListPanel.tsx:
  Lista condivisioni attive per documento/protocollo:
  - Ogni riga: destinatario, tipo (interno/esterno), scadenza, 
    accessi (N/max o N/illimitato), stato (attivo/scaduto), 
    bottone "Revoca"
  - Badge "Scaduto" / "Revocato" per condivisioni non più valide
  - Bottone "+ Nuova condivisione" in cima

Aggiorna DocumentDetailPanel.tsx (Fase 3):
  - Aggiungi Tab "Condivisioni" con ShareListPanel + bottone nuova condivisione
  - Bottone "Condividi" anche nell'header del panel (accesso rapido)

Aggiorna ProtocolsPage.tsx (Fase 6):
  - Aggiungi azione "Condividi" nella tabella protocolli

Crea `frontend/src/pages/PublicSharePage.tsx` (route: /share/:token, PUBBLICA):
  Pagina accessibile senza login.
  
  Stati possibili:
  1. Caricamento: spinner
  2. Richiede password: 
     - Form con input password + bottone "Accedi"
     - Messaggio errore se password sbagliata
  3. Valido: 
     - Header: "Documento condiviso da [Nome Cognome]"
     - Card con: titolo documento, descrizione, versione, stato
     - Metadati: data condivisione, scadenza (se presente)
     - Bottone "Scarica documento" (se can_download=True)
     - Nota: "Accesso in sola lettura. Effettua il login per ulteriori azioni."
  4. Scaduto / Revocato:
     - Messaggio: "Questo link non è più valido."
     - Bottone "Vai al login"
  5. Non trovato: 404 message

TEST Vitest:
  - ShareModal: toggle interno/esterno, copia link dopo condivisione
  - ShareListPanel: render lista, revoca
  - PublicSharePage: stati loading, password richiesta, valido, scaduto

Esegui: `npm run test -- --run`
Esegui: `npm run build`
```

---

## TEST INTEGRAZIONE FASE 9A

### Prompt per Cursor:

```
Test di integrazione Fase 9A.

1. `pytest backend/apps/sharing/ -v --cov=apps/sharing`

2. `npm run test -- --run`

3. Test manuale:

   Condivisione interna:
   a) Apri documento → tab "Condivisioni" → "Nuova condivisione"
   b) Seleziona utente interno (operatore@test.com)
   c) Scadenza: 7 giorni, download: sì
   d) Condividi → notifica inviata a operatore
   e) Login come operatore → notifica visibile → click → documento aperto
   f) Verifica: operatore ora ha can_read sul documento
   
   Condivisione esterna:
   g) Nuova condivisione → utente esterno → email esterno@esempio.com
   h) Scadenza: 1 giorno, password: "secret123"
   i) Condividi → link generato → copia link
   j) Apri il link in finestra anonima (non loggato)
   k) Pagina richiede password → inserisci "secret123" → accesso
   l) Documento visibile → download funziona
   m) Inserisci password sbagliata → errore
   
   Scadenza e revoca:
   n) Crea condivisione con scadenza 0 giorni (ieri, simula manualmente
      nel DB: expires_at = now() - 1 day)
   o) Accedi al link → 410 "Link non più valido"
   p) Revoca condivisione attiva → link non funziona più → 410

4. AuditLog:
   GET /api/audit/?action=document_shared → entries presenti

Crea `FASE_09A_TEST_REPORT.md`.
```
