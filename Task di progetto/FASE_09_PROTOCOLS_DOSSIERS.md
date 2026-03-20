# AXDOC — FASE 09
# Protocollazione e Fascicoli

## Obiettivo
Implementare la protocollazione documenti con numerazione progressiva
e il sistema di fascicoli per l'organizzazione documentale.

**Prerequisito: FASE 08 completata e tutti i test passanti.**

---

## CHECKLIST DI COMPLETAMENTO

- [ ] CRUD protocolli (RF-058..RF-063)
- [ ] Numerazione progressiva per anno e per UO (RF-059)
- [ ] Registrazione data e ora automatica (RF-060)
- [ ] Protocolli in entrata e uscita (RF-061)
- [ ] Blocco modifica documento protocollato (RF-063)
- [ ] Fascicolazione protocolli (RF-062)
- [ ] CRUD fascicoli (RF-064..RF-069)
- [ ] Assegnazione responsabile fascicolo (RF-069)
- [ ] Archiviazione fascicolo (RF-066)
- [ ] Associazione documenti ai fascicoli (RF-068)
- [ ] Filtri protocolli: tutti / in entrata / in uscita
- [ ] Filtri fascicoli: i miei / tutti / archiviati
- [ ] Frontend: pagina protocollazione
- [ ] Frontend: pagina fascicoli
- [ ] Tutti i test passano

---

## STEP 6.1 — App Protocols: Modelli e API

### Prompt per Cursor:

```
Crea `backend/apps/protocols/` per la protocollazione documenti.

Requisiti: RF-058..RF-063

Crea `backend/apps/protocols/models.py`:

PROTOCOL_DIRECTION = [('in', 'In entrata'), ('out', 'In uscita')]
PROTOCOL_STATUS = [('active', 'Attivo'), ('archived', 'Archiviato')]

class ProtocolCounter(models.Model):
  """Contatore progressivo per anno + UO"""
  - organizational_unit: FK OrganizationalUnit
  - year: IntegerField
  - last_number: IntegerField default 0
  
  Meta: unique_together = ['organizational_unit', 'year']
  
  @classmethod
  def get_next_number(cls, ou, year) → int:
    Atomico (select_for_update), incrementa e ritorna last_number

class Protocol(models.Model):
  - id: UUID primary key
  - number: IntegerField (progressivo)
  - year: IntegerField (anno di protocollazione)
  - organizational_unit: FK OrganizationalUnit
  - protocol_id: CharField (generato: "{year}/{OU.code}/{number:04d}")
    Es: "2024/IT/0042"
  - direction: CharField choices PROTOCOL_DIRECTION
  - document: FK Document null=True (documento protocollato interno)
  - subject: CharField max 500 (oggetto del protocollo)
  - sender_receiver: CharField max 500 
    (mittente se in, destinatario se out)
  - registered_at: DateTimeField auto_now_add (RF-060)
  - registered_by: FK User
  - status: CharField choices PROTOCOL_STATUS default 'active'
  - notes: TextField blank=True
  - attachments: ManyToMany Document related_name='protocol_attachments'
  
  Meta: unique_together = ['organizational_unit', 'year', 'number']

Crea `backend/apps/protocols/serializers.py`:
  - ProtocolListSerializer
  - ProtocolDetailSerializer (con documento e allegati)
  - ProtocolCreateSerializer

Crea `backend/apps/protocols/views.py`:

ProtocolViewSet:
  - list: GET /api/protocols/
    - Filtraggio: direction (in/out/all), ou_id, year, status
    - Ricerca: subject, sender_receiver, protocol_id
    - Ordinamento: registered_at desc default
    - Solo protocolli della propria UO (o ADMIN vede tutti)
    - Query param `filter=mine` / `filter=all` (collaudo)
  
  - retrieve: dettaglio completo
  
  - create: POST /api/protocols/
    - Campi: direction, document_id (opz), subject, sender_receiver, 
      organizational_unit_id, notes
    - Genera automaticamente number (ProtocolCounter.get_next_number())
    - Genera protocol_id
    - Registra registered_at = now()
    - Se document fornito: imposta Document.is_protocolled = True
      e blocca modifiche (RF-063)
  
  - update: PATCH (solo subject, sender_receiver, notes) (RF-063 — no modifica doc)
  
  - destroy: 400 — i protocolli non si eliminano (solo archiviano)
  
  Extra:
  - POST /api/protocols/{id}/archive/: archivia protocollo
  - GET /api/protocols/{id}/download/: scarica documento protocollato
  - POST /api/protocols/{id}/add_attachment/: aggiunge allegato (documento esistente)
  - POST /api/documents/{id}/protocollo/: crea protocollo dal documento
    (shortcut: crea Protocol con direction='out', document=questo documento)

Modifica `backend/apps/documents/models.py`:
  - Aggiungi: is_protocolled = BooleanField default False
  - In DocumentViewSet upload_version e update:
    se document.is_protocolled → 400 "Documento protocollato non modificabile" (RF-063)

Aggiorna migrations

TEST `backend/apps/protocols/tests/`:
  - Creazione protocollo: number incrementale per anno/UO
  - Due UO separate: contatori indipendenti
  - protocol_id formato corretto (es. "2024/IT/0001")
  - Nuovo anno: numero riparte da 1
  - Documento protocollato non modificabile: upload_version → 400
  - Filtro direction funzionante
  - Ricerca per subject, protocol_id

Esegui: `pytest backend/apps/protocols/ -v --tb=short`
```

---

## STEP 6.2 — App Dossiers: Fascicoli

### Prompt per Cursor:

```
Crea `backend/apps/dossiers/` per la gestione dei fascicoli.

Requisiti: RF-064..RF-069

Crea `backend/apps/dossiers/models.py`:

DOSSIER_STATUS = [
  ('open', 'Aperto'),
  ('archived', 'Archiviato'),
  ('closed', 'Chiuso'),
]

class Dossier(models.Model):
  - id: UUID primary key
  - title: CharField max 500
  - identifier: CharField max 100 unique (codice fascicolo)
  - description: TextField blank=True
  - status: CharField choices DOSSIER_STATUS default 'open'
  - responsible: FK User related_name='responsible_dossiers' (RF-069)
  - created_by: FK User
  - created_at, updated_at: timestamps
  - archived_at: DateTimeField null=True
  - is_deleted: bool default False
  
  # Accesso
  - allowed_users: ManyToMany User through DossierPermission
  - allowed_ous: ManyToMany OrganizationalUnit through DossierOUPermission
  
  Metodo: get_documents(): tutti i documenti nel fascicolo
  Metodo: get_protocols(): tutti i protocolli fasciolati

class DossierDocument(models.Model):
  """Documenti nel fascicolo"""
  - dossier: FK Dossier
  - document: FK Document
  - added_by: FK User
  - added_at: auto_now_add
  - notes: CharField blank=True
  Meta: unique_together = ['dossier', 'document']

class DossierProtocol(models.Model):
  """Protocolli fasciolati"""
  - dossier: FK Dossier
  - protocol: FK Protocol
  - added_by: FK User
  - added_at: auto_now_add
  Meta: unique_together = ['dossier', 'protocol']

class DossierPermission(models.Model):
  - dossier: FK Dossier
  - user: FK User
  - can_read: bool default True
  - can_write: bool default False
  Meta: unique_together = ['dossier', 'user']

class DossierOUPermission(models.Model):
  - dossier: FK Dossier
  - organizational_unit: FK OrganizationalUnit
  - can_read: bool default True
  Meta: unique_together = ['dossier', 'organizational_unit']

Crea `backend/apps/dossiers/views.py`:

DossierViewSet:
  - list: GET /api/dossiers/
    - Query param `filter=mine` → fascicoli dove current_user è responsabile O ha permesso
    - Query param `filter=all` → tutti (solo ADMIN vede tutti)
    - Query param `status=archived` → solo archiviati
    - Default: status != 'archived'
    - Ordinamento: updated_at desc
  
  - retrieve: con documenti, protocolli, responsabile, utenti con accesso
  
  - create: solo ADMIN o APPROVER
    - identifier deve essere unico
    - Campi: title, identifier, description, responsible_id, 
      allowed_users[], allowed_ous[]
  
  - update: responsabile O ADMIN
  
  - destroy: soft delete, solo ADMIN, 400 se status != 'open'
  
  Extra:
  - POST /api/dossiers/{id}/archive/: archivia (RF-066)
    → status = 'archived', archived_at = now()
    → 400 se ha documenti in lavorazione (status != APPROVED)
  - POST /api/dossiers/{id}/add_document/: aggiunge documento
    → Corpo: {"document_id": "...", "notes": "..."}
  - DELETE /api/dossiers/{id}/remove_document/{doc_id}/
  - POST /api/dossiers/{id}/add_protocol/: fascicola protocollo (RF-062)
  - DELETE /api/dossiers/{id}/remove_protocol/{proto_id}/
  - GET /api/dossiers/{id}/documents/: lista documenti nel fascicolo
  - GET /api/dossiers/{id}/protocols/: lista protocolli nel fascicolo

TEST `backend/apps/dossiers/tests/`:
  - CRUD fascicolo
  - Identificatore univoco: duplicato → 400
  - Archiviazione: con documenti non approvati → 400; con tutti approvati → OK
  - Filtro mine: solo fascicoli dell'utente
  - Filtro archived: solo archiviati
  - Aggiunta/rimozione documento
  - Fascicolazione protocollo
  - Utente senza permesso → 403

Esegui: `pytest backend/apps/dossiers/ -v --tb=short`
```

---

## STEP 6.3 — Frontend: Protocolli e Fascicoli

### Prompt per Cursor:

```
Crea le pagine di protocollazione e fascicoli nel frontend.

Aggiungi servizi:
  - `frontend/src/services/protocolService.ts`
  - `frontend/src/services/dossierService.ts`

Crea `frontend/src/components/protocols/`:

ProtocolTable.tsx:
  - Colonne: ID protocollo, oggetto, direzione (badge IN/OUT), 
    mittente/destinatario, UO, data registrazione, stato, azioni
  - Filtri: direzione (tutti/entrata/uscita), anno, UO, stato
  - Ricerca testuale
  - Azione: visualizza, download, archivia, aggiungi a fascicolo

ProtocolFormModal.tsx:
  - Tipo: In entrata / In uscita
  - Oggetto (obbligatorio)
  - Mittente/Destinatario
  - Unità Organizzativa
  - Documento collegato (select documenti esistenti, opzionale)
  - Note
  - Mostra protocol_id generato (read-only, visualizzato dopo creazione)

Crea `frontend/src/components/dossiers/`:

DossierList.tsx:
  - Cards o tabella con: identificatore, titolo, responsabile, 
    nr documenti, nr protocolli, stato, data aggiornamento
  - Tabs: "I miei fascicoli" / "Tutti i fascicoli" / "Archiviati"
  - Azioni: apri, modifica, archivia, elimina

DossierDetailPage.tsx (route: /dossiers/:id):
  - Header: titolo, identificatore, responsabile, stato, data
  - Tab "Documenti": lista con DossierDocument, add/remove
  - Tab "Protocolli": lista con DossierProtocol, add/remove  
  - Tab "Accessi": chi può vedere il fascicolo (solo ADMIN/responsabile)
  - Bottone "Archivia Fascicolo" (con conferma)

DossierFormModal.tsx:
  - Titolo, identificatore (auto-suggerito), descrizione
  - Responsabile (select utenti)
  - Accesso: aggiungi utenti / UO

Modifica DocumentDetailPanel (da Fase 3):
  - Tab "Protocolli": lista protocolli associati + bottone "Protocolla"
  - Bottone "Protocolla" apre ProtocolFormModal precompilato

Crea pagine:
  
ProtocolsPage.tsx (route: /protocols):
  - ProtocolTable con paginazione
  - Bottone "Nuovo Protocollo"

DossiersPage.tsx (route: /dossiers):
  - DossierList
  - Bottone "Nuovo Fascicolo"

TEST Vitest:
  - ProtocolTable: render, filtri direzione
  - ProtocolFormModal: validazione campi
  - DossierList: tabs, render cards
  - DossierDetailPage: tabs, aggiunta documento

Esegui: `npm run test -- --run`
Esegui: `npm run build`
```

---

## TEST INTEGRAZIONE FASE 6

### Prompt per Cursor:

```
Test di integrazione Fase 6.

1. `pytest apps/protocols/ apps/dossiers/ -v --cov`

2. `npm run test -- --run`

3. Test manuale:
   
   Protocollazione:
   a) Crea protocollo in entrata per UO "IT":
      protocol_id dovrebbe essere "2024/IT/0001"
   b) Crea secondo protocollo stesso UO → "2024/IT/0002"
   c) Crea protocollo per UO "Direzione" → "2024/DIR/0001" (contatore separato)
   d) Protocolla documento esistente (out) → documento diventa is_protocolled=True
   e) Prova upload nuova versione documento protocollato → 400 con messaggio
   f) GET /api/protocols/?filter=in → solo entrata
   g) GET /api/protocols/?direction=out → solo uscita
   
   Fascicoli:
   h) Crea fascicolo "Contratti 2024" con identificatore "CONTR-2024"
   i) Aggiungi 2 documenti al fascicolo
   j) Fascicola protocollo nel fascicolo
   k) Prova archiviare con documento non approvato → 400
   l) Approva tutti i documenti tramite workflow (usa Fase 5)
   m) Archivia fascicolo → status = ARCHIVED
   n) GET /api/dossiers/?status=archived → mostra fascicolo archiviato
   o) GET /api/dossiers/ default → NON mostra archiviato
   p) Prova accesso fascicolo da utente senza permesso → 403

4. Browser:
   - /protocols mostra tabella con filtri
   - Nuovo protocollo genera ID automatico
   - /dossiers mostra list e dettaglio
   - DocumentDetailPanel mostra tab Protocolli

Crea `FASE_06_TEST_REPORT.md`.
```
