# AXDOC — FASE 12
# Ricerca Full-Text, Notifiche e Audit Log

## Obiettivo
Implementare la ricerca full-text su documenti, il sistema di notifiche
in-app e l'audit log completo delle attività.

**Prerequisito: FASE 08 completata e tutti i test passanti.**

---

## CHECKLIST DI COMPLETAMENTO

- [ ] Ricerca per nome documento (RF-070)
- [ ] Ricerca per metadati (RF-071)
- [ ] Ricerca full-text nel contenuto file (RF-072) — MySQL FULLTEXT
- [ ] Filtri avanzati (RF-073)
- [ ] Ordinamento risultati (RF-074)
- [ ] Notifiche in-app per workflow (RF-057)
- [ ] Notifiche cliccabili con redirect (feedback collaudo)
- [ ] "Segna tutte come lette" (feedback collaudo)
- [ ] Vista notifiche lette/non lette (feedback collaudo)
- [ ] Audit log completo (RNF-007)
- [ ] Sezione "Attività" per ogni documento
- [ ] Frontend: barra di ricerca globale
- [ ] Frontend: pagina ricerca con filtri avanzati
- [ ] Frontend: panel notifiche
- [ ] Tutti i test passano

---

## STEP 7.1 — Sistema Notifiche

### Prompt per Cursor:

```
Crea `backend/apps/notifications/` per le notifiche in-app.

Requisiti: RF-057, feedback collaudo notifiche

Crea `backend/apps/notifications/models.py`:

NOTIFICATION_TYPE = [
  ('workflow_assigned', 'Workflow assegnato'),
  ('workflow_approved', 'Documento approvato'),
  ('workflow_rejected', 'Documento rifiutato'),
  ('workflow_changes_requested', 'Modifiche richieste'),
  ('workflow_completed', 'Workflow completato'),
  ('document_shared', 'Documento condiviso'),
  ('mention', 'Menzione'),
  ('system', 'Sistema'),
]

class Notification(models.Model):
  - id: UUID primary key
  - recipient: FK User related_name='notifications'
  - notification_type: CharField choices NOTIFICATION_TYPE
  - title: CharField max 300
  - body: TextField
  - is_read: bool default False
  - read_at: DateTimeField null=True
  - created_at: auto_now_add
  
  # Link contestuale (per redirect al click — feedback collaudo)
  - content_type: FK ContentType null=True (per generic FK)
  - object_id: UUIDField null=True
  - link_url: CharField max 500 blank=True
    (Es: "/documents/{id}" o "/workflows/{id}")
  
  - metadata: JSONField default=dict (dati extra per renderizzare)

Crea `backend/apps/notifications/services.py`:

NotificationService:
  - send(recipient, type, title, body, link_url='', metadata={}): crea Notification
  - send_bulk(recipients, ...): crea per lista utenti
  - notify_workflow_assigned(step_instance): notifica assegnati
  - notify_workflow_completed(instance): notifica started_by
  - notify_workflow_rejected(instance, comment): notifica started_by  
  - notify_changes_requested(instance, comment): notifica document creator
  - notify_document_shared(document, shared_with_user): notifica utente

Crea `backend/apps/notifications/views.py`:

NotificationViewSet:
  - list: GET /api/notifications/
    - Solo notifiche del current_user
    - Query param `unread=true` → solo non lette
    - Query param `read=true` → solo lette (feedback collaudo)
    - Ordinamento: created_at desc
    - Paginazione: 20 per pagina
  
  - retrieve: singola notifica (e la marca come letta)
  
  Extra:
  - POST /api/notifications/mark_read/: 
    Corpo: {"ids": [...]} O {"all": true} → segna lette (RF feedback)
  - GET /api/notifications/unread_count/: ritorna {"count": N}

Integra NotificationService nel workflow:
  Modifica `backend/apps/workflows/views.py`:
  - In start_workflow: chiama notify_workflow_assigned
  - In workflow_action approve last step: notify_workflow_completed
  - In workflow_action reject: notify_workflow_rejected
  - In workflow_action request_changes: notify_changes_requested

Aggiungi WebSocket o polling endpoint:
  GET /api/notifications/poll/:
  - Ritorna unread_count aggiornato
  - Usato dal frontend per polling ogni 30s

TEST `backend/apps/notifications/tests/`:
  - Notifica creata a workflow_assigned
  - Notifica completamento a started_by dopo ultimo approve
  - mark_read singola: is_read=True
  - mark_read all: tutte le notifiche dell'utente lette
  - unread_count corretto
  - Utente A non vede notifiche utente B

Esegui: `pytest backend/apps/notifications/ -v --tb=short`
```

---

## STEP 7.2 — Ricerca Avanzata

### Prompt per Cursor:

```
Crea `backend/apps/search/` per la ricerca full-text e avanzata.

Requisiti: RF-070..RF-074

Strategia di ricerca:
  - MySQL FULLTEXT index per ricerca nel titolo e contenuto indicizzato
  - Django ORM per filtri su metadati
  - I file PDF/DOCX/TXT vengono indicizzati al momento dell'upload

Crea `backend/apps/search/models.py`:

class DocumentIndex(models.Model):
  """Contenuto estratto dai file per full-text search"""
  - document: OneToOne → Document
  - document_version: FK DocumentVersion (versione indicizzata)
  - content: TextField (testo estratto dal file)
  - indexed_at: auto_now
  - error_message: CharField blank=True (se estrazione fallita)
  
  Meta: indexes = [models.Index(fields=['document'])]

Crea `backend/apps/search/extractors.py`:
  Funzione extract_text(file_path, mime_type) → str:
  - Per text/*: legge direttamente
  - Per application/pdf: usa PyPDF2 o pdfminer.six
  - Per application/vnd.openxmlformats-officedocument.wordprocessingml: python-docx
  - Per altri: ritorna '' (non indicizzabile, no errore)
  
  Aggiorna requirements.txt con: PyPDF2, python-docx

Crea `backend/apps/search/tasks.py`:
  index_document(document_version_id): 
  - Estrae testo dalla versione
  - Salva/aggiorna DocumentIndex
  - Chiamato sincrono (non celery, per semplicità) dopo upload

Modifica DocumentViewSet (apps/documents/views.py):
  - Dopo creazione nuova versione: chiama index_document(version.id)

Crea `backend/apps/search/views.py`:

SearchView (GET /api/search/):
  Query params:
  - q: testo libero (RF-070, RF-072)
  - type: 'documents'|'protocols'|'dossiers' (default: documents)
  - folder_id: filtra per cartella
  - metadata_structure_id: filtra per struttura
  - metadata_{field_name}: filtra per valore metadato specifico (RF-071)
    Es: /api/search/?q=contratto&metadata_fornitore=Acme
  - status: filtra per status documento
  - created_by: filtra per autore
  - date_from, date_to: range date
  - order_by: relevance|title|date|-date (RF-074)
  - page, page_size
  
  Logica di ricerca:
  1. Parte da Document.objects filtrati per permessi (CanAccessDocument)
  2. Se q presente:
     - LIKE %q% su Document.title (RF-070)
     - JOIN con DocumentIndex, LIKE %q% su content (RF-072)
     - Combina con OR
  3. Applica filtri metadata: 
     metadata_values__fornitore__icontains=valore (RF-071)
  4. Applica altri filtri
  5. Ordina per rilevanza (titolo match > content match) o campo
  
  Risponde con:
  - results: lista documenti con snippet (frammento testo con match)
  - total_count
  - facets: aggregazioni per status, metadata_structure, cartella
    (per mostrare filtri con conteggi)

Crea `backend/apps/search/serializers.py`:
  - SearchResultSerializer: documento + snippet + score

TEST `backend/apps/search/tests/`:
  - Ricerca per titolo: trova documenti con titolo matching
  - Ricerca full-text: dopo indicizzazione, trova per contenuto
  - Filtro metadato specifico funzionante
  - Ricerca per utente senza permesso: non trova documenti altrui
  - Risultati ordinati per data

Esegui: `pytest backend/apps/search/ -v --tb=short`
```

---

## STEP 7.3 — Audit Log Completo

### Prompt per Cursor:

```
Completa e potenzia l'app Audit già iniziata in authentication.

Requisiti: RNF-007, RF-010, sezione "Attività" collaudo

Sposta/migra AuditLog da authentication a `backend/apps/audit/`:

Aggiorna `backend/apps/audit/models.py`:

AUDIT_ACTIONS = [
  # Auth
  ('login', 'Login'), ('logout', 'Logout'),
  ('password_reset', 'Reset password'), ('mfa_enabled', 'MFA abilitato'),
  # Documents  
  ('document_created', 'Documento creato'),
  ('document_viewed', 'Documento visualizzato'),
  ('document_downloaded', 'Documento scaricato'),
  ('document_updated', 'Documento modificato'),
  ('document_deleted', 'Documento eliminato'),
  ('document_version_uploaded', 'Nuova versione caricata'),
  ('document_locked', 'Documento bloccato'),
  ('document_unlocked', 'Documento sbloccato'),
  ('document_shared', 'Documento condiviso'),
  # Workflow
  ('workflow_started', 'Workflow avviato'),
  ('workflow_action', 'Azione workflow'),
  ('workflow_completed', 'Workflow completato'),
  # Protocol
  ('protocol_created', 'Protocollo creato'),
  # Dossier
  ('dossier_created', 'Fascicolo creato'),
  ('dossier_archived', 'Fascicolo archiviato'),
  # Users
  ('user_created', 'Utente creato'),
  ('user_invited', 'Utente invitato'),
  ('user_disabled', 'Utente disabilitato'),
]

class AuditLog(models.Model):
  - id: UUID primary key
  - user: FK User null=True (null per azioni di sistema)
  - action: CharField choices AUDIT_ACTIONS
  - target_type: CharField (es: 'document', 'user', 'protocol')
  - target_id: UUIDField null=True
  - target_repr: CharField (es: titolo documento al momento dell'azione)
  - detail: JSONField default=dict (dati aggiuntivi specifici per azione)
  - ip_address: GenericIPAddressField null=True
  - user_agent: TextField blank=True
  - timestamp: auto_now_add

Crea `backend/apps/audit/middleware.py`:
  AuditMiddleware: estrae IP e user-agent da ogni request,
  li rende disponibili nel thread locale per AuditLog.log()

Crea `backend/apps/audit/services.py`:
  AuditService.log(user, action, target=None, detail={}, request=None):
  Crea AuditLog in modo asincrono (direct save per semplicità).

Integra AuditService nei view principali:
  - DocumentViewSet: create, update, destroy, download, lock/unlock
  - WorkflowInstance: start, action
  - ProtocolViewSet: create
  - DossierViewSet: create, archive
  - UserViewSet: create, update, destroy

Crea `backend/apps/audit/views.py`:

AuditLogViewSet (read-only):
  - list: GET /api/audit/
    - Solo ADMIN può vedere tutto
    - Altri utenti: solo log relativi ai propri documenti
    - Filtraggio: user_id, action, target_type, target_id, date_from, date_to
    - Ordinamento: timestamp desc
    - Paginazione: 50 per pagina
  
  Extra:
  - GET /api/audit/document/{doc_id}/: attività specifiche di un documento
    Usato da DocumentDetailPanel tab "Attività"

TEST `backend/apps/audit/tests/`:
  - Download documento → AuditLog creato con action='document_downloaded'
  - Login → AuditLog con action='login' e IP corretto
  - ADMIN vede tutti i log
  - Non-ADMIN vede solo log propri documenti

Esegui: `pytest backend/apps/audit/ -v --tb=short`
```

---

## STEP 7.4 — Frontend: Ricerca e Notifiche

### Prompt per Cursor:

```
Implementa ricerca e notifiche nel frontend.

Aggiungi servizi:
  - `frontend/src/services/searchService.ts`
  - `frontend/src/services/notificationService.ts`
  - `frontend/src/services/auditService.ts`

Crea `frontend/src/components/search/`:

GlobalSearchBar.tsx:
  - Input di ricerca nella navbar principale
  - Dropdown con risultati live mentre si digita (debounce 300ms)
  - Max 5 risultati nel dropdown, link "Vedi tutti"
  - Icona di loading durante ricerca
  - Risultati: icona tipo, titolo, cartella, data

SearchPage.tsx (route: /search):
  - Input ricerca prominente
  - Filtri laterali:
    * Tipo (documenti/protocolli/fascicoli)
    * Struttura metadati (select dinamica)
    * Cartella
    * Stato documento
    * Autore
    * Data da/a
    * Campi metadati dinamici (se selezionata struttura)
  - Risultati con snippet evidenziato
  - Ordinamento: pertinenza / titolo / data
  - Paginazione

SearchResultCard.tsx:
  - Titolo con testo corrispondente in grassetto (highlight)
  - Snippet del contenuto con match evidenziato
  - Badge stato, struttura metadati, cartella
  - Data creazione, autore
  - Bottoni: apri, download

Crea `frontend/src/components/notifications/`:

NotificationBell.tsx:
  - Icona campanella nella navbar
  - Badge rosso con unread_count
  - Polling ogni 30 secondi per aggiornare count
  - Click → apre NotificationPanel

NotificationPanel.tsx:
  - Panel slide-in a destra
  - Header con "Notifiche" + bottone "Segna tutte come lette" (feedback collaudo)
  - Tabs: "Non lette" / "Tutte" (feedback collaudo)
  - Lista notifiche: icona tipo, titolo, corpo abbreviato, data relativa
  - Click su notifica → naviga a link_url + marca come letta (feedback collaudo)
  - Infinite scroll o paginazione

NotificationItem.tsx:
  - Layout: icona + contenuto + data
  - Sfondo diverso per non lette
  - Click naviga e segna come letta

Crea `frontend/src/components/audit/`:

ActivityTimeline.tsx:
  - Usato nel DocumentDetailPanel tab "Attività"
  - Lista eventi in ordine cronologico inverso
  - Ogni evento: icona azione, testo descrittivo, utente, data
  - Es: "Mario Rossi ha caricato la versione 2 — 14 marzo 2024 ore 10:30"

Aggiorna layout principale (`frontend/src/components/Layout.tsx`):
  - GlobalSearchBar nella navbar
  - NotificationBell nella navbar
  - Inizializzazione polling notifiche al mount

Aggiorna DocumentDetailPanel:
  - Tab "Attività" con ActivityTimeline

TEST Vitest:
  - GlobalSearchBar: debounce, dropdown risultati
  - NotificationBell: mostra badge con count
  - NotificationPanel: tabs lette/non lette, mark all read
  - ActivityTimeline: render eventi in ordine

Esegui: `npm run test -- --run`
Esegui: `npm run build`
```

---

## TEST INTEGRAZIONE FASE 7

### Prompt per Cursor:

```
Test di integrazione Fase 7.

1. `pytest apps/search/ apps/notifications/ apps/audit/ -v --cov`

2. `npm run test -- --run`

3. Test manuale ricerca:
   a) Carica documento PDF con testo "report annuale vendite 2024"
      → aspetta indicizzazione → cerca "vendite" → trova documento
   b) Carica documento con metadati: fornitore="Acme Corp"
      → cerca /api/search/?metadata_fornitore=Acme → trova documento
   c) Ricerca con filtro data_from → esclude documenti vecchi
   d) Ricerca con q="inesistente_xyz" → risultati vuoti (no errori)

4. Test notifiche:
   a) Avvia workflow su documento
   b) Login come revisore → notifica nella campanella
   c) Click sulla notifica → naviga al documento corretto
   d) "Segna tutte come lette" → count a 0
   e) Tab "Tutte" → mostra anche notifiche lette

5. Test audit:
   a) Scarica documento → GET /api/audit/document/{id}/ → entry download presente
   b) Login → GET /api/audit/?action=login → entry presente con IP
   c) Login come operatore → GET /api/audit/ → vede solo suoi log, non quelli admin

6. Browser:
   - Barra ricerca in navbar funziona
   - /search con filtri funziona
   - Campanella notifiche aggiornata in tempo reale
   - Panel notifiche con tabs

Crea `FASE_07_TEST_REPORT.md`.
```
