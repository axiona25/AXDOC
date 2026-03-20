# AXDOC — FASE 05
# Gestione Documenti, Cartelle e Versioning

## Obiettivo
Implementare il cuore del sistema documentale: gestione documenti,
cartelle, upload/download, versioning, allegati e permessi.

**Prerequisito: FASE 02 completata e tutti i test passanti.**

---

## CHECKLIST DI COMPLETAMENTO

- [ ] API CRUD Cartelle funzionante con gerarchia
- [ ] API CRUD Documenti con upload file
- [ ] Download documento funzionante
- [ ] Versioning documentale (RF-033): ogni salvataggio crea nuova versione
- [ ] Storico modifiche visibile (RF-034)
- [ ] Blocco documento in modifica (RF-037): lock/unlock
- [ ] Gestione allegati (RF-036)
- [ ] Copia documento (RF-038)
- [ ] Spostamento tra cartelle (RF-039)
- [ ] Permessi: documento visibile solo a utenti/UO assegnati
- [ ] Upload fino a 200MB (RNF-011)
- [ ] Frontend: file explorer con navigazione cartelle
- [ ] Frontend: upload con progress bar
- [ ] Frontend: viewer documento (almeno PDF/immagini)
- [ ] Tutti i test passano

---

## STEP 3.1 — App Documents: Modelli

### Prompt per Cursor:

```
Crea `backend/apps/documents/` con i modelli per documenti e cartelle.

Requisiti: RF-028..RF-039

Crea `backend/apps/documents/models.py`:

class Folder(models.Model):
  - id: UUID primary key
  - name: CharField max 255
  - parent: FK a self null=True related_name='subfolders'
  - created_by: FK User
  - created_at, updated_at: timestamps
  - is_deleted: bool default False
  
  Metodo: get_path() → stringa "root/cartella/sottocartella"
  Metodo: get_ancestors() → lista folder parent

class Document(models.Model):
  STATUS = [DRAFT, IN_REVIEW, APPROVED, ARCHIVED, REJECTED]
  
  - id: UUID primary key
  - title: CharField max 500
  - description: TextField blank=True
  - folder: FK Folder null=True
  - status: CharField choices STATUS, default DRAFT
  - current_version: IntegerField default 1
  - created_by: FK User
  - created_at, updated_at: timestamps
  - is_deleted: bool default False
  - metadata_structure: FK MetadataStructure null=True (collegamento fase 4)
  - metadata_values: JSONField default=dict
  - locked_by: FK User null=True (RF-037)
  - locked_at: DateTimeField null=True
  
  # Permessi
  - allowed_users: ManyToMany User through DocumentPermission
  - allowed_ous: ManyToMany OrganizationalUnit through DocumentOUPermission

class DocumentVersion(models.Model):
  - id: UUID primary key
  - document: FK Document related_name='versions'
  - version_number: IntegerField
  - file: FileField upload_to='documents/%Y/%m/'
  - file_name: CharField (nome originale)
  - file_size: BigIntegerField (bytes)
  - file_type: CharField (mime type)
  - checksum: CharField (SHA256 del file)
  - created_by: FK User
  - created_at: auto_now_add
  - change_description: TextField blank=True
  - is_current: bool default True
  
  Meta: unique_together = ['document', 'version_number']

class DocumentAttachment(models.Model):
  - id: UUID primary key
  - document: FK Document related_name='attachments'
  - file: FileField upload_to='attachments/%Y/%m/'
  - file_name: CharField
  - file_size: BigIntegerField
  - file_type: CharField
  - uploaded_by: FK User
  - uploaded_at: auto_now_add
  - description: CharField blank=True

class DocumentPermission(models.Model):
  - document: FK Document
  - user: FK User
  - can_read: bool default True
  - can_write: bool default False
  - can_delete: bool default False
  Meta: unique_together = ['document', 'user']

class DocumentOUPermission(models.Model):
  - document: FK Document
  - organizational_unit: FK OrganizationalUnit
  - can_read: bool default True
  - can_write: bool default False
  Meta: unique_together = ['document', 'organizational_unit']

Crea le migrations con `makemigrations documents`
```

---

## STEP 3.2 — API Cartelle

### Prompt per Cursor:

```
Crea le API per la gestione delle Cartelle in `backend/apps/documents/views.py`.

FolderViewSet:
  - list: GET /api/folders/
    - Query param `parent_id`: se null → root folders; se id → sottocartelle
    - Query param `all=true` → struttura completa ad albero
    - Solo cartelle visibili all'utente (ha almeno un documento accessibile)
  - retrieve: GET /api/folders/{id}/ con subfolders e conteggio documenti
  - create: POST /api/folders/ (tutti gli utenti autenticati)
    - Valida: nome non duplicato nello stesso parent
  - update: PATCH /api/folders/{id}/ (solo chi ha creato o ADMIN)
  - destroy: DELETE /api/folders/{id}/ (soft delete)
    - 400 se cartella contiene documenti non eliminati
  
  Extra:
  - GET /api/folders/{id}/breadcrumb/ → lista antenati per navigazione

FolderSerializer:
  - FolderListSerializer: id, name, parent_id, subfolder_count, document_count, created_at
  - FolderDetailSerializer: come sopra + subfolders (nested, 1 livello)
  - FolderCreateSerializer: name, parent_id

Crea `backend/apps/documents/permissions.py`:
  class CanAccessDocument(BasePermission):
    - Verifica che l'utente sia in DocumentPermission O
      che l'utente appartenga a una UO in DocumentOUPermission O
      che l'utente sia ADMIN O
      che il documento sia stato creato dall'utente

TEST `backend/apps/documents/tests/test_folders.py`:
  - Creazione cartella root e sottocartella
  - Duplicato nome stesso parent → 400
  - Breadcrumb corretto per 3 livelli di profondità
  - Soft delete cartella vuota → 200
  - Soft delete cartella con documenti → 400
  - Listing root folders: non mostra soft deleted

Esegui: `pytest backend/apps/documents/tests/test_folders.py -v`
```

---

## STEP 3.3 — API Documenti con Upload

### Prompt per Cursor:

```
Crea le API per i Documenti con upload/download in `backend/apps/documents/views.py`.

Configurazione Django per file grandi:
  In settings/base.py aggiungi:
  - DATA_UPLOAD_MAX_MEMORY_SIZE = 209715200  # 200MB (RNF-011)
  - FILE_UPLOAD_MAX_MEMORY_SIZE = 209715200

DocumentViewSet:
  - list: GET /api/documents/
    - Filtraggio: folder_id, status, created_by, title (contains), metadata_structure_id
    - Ordinamento: title, created_at, updated_at, status
    - Paginazione: 20 per pagina
    - Solo documenti accessibili all'utente (usa CanAccessDocument)
    - Query param `folder_id=null` → documenti senza cartella (root)
  
  - retrieve: GET /api/documents/{id}/
    - Versione corrente + lista versioni
    - Allegati
    - Permessi dell'utente sul documento (can_read, can_write, can_delete)
  
  - create: POST /api/documents/ (multipart/form-data)
    - Campi: title, description, folder_id, file (obbligatorio), 
      metadata_structure_id, allowed_users[], allowed_ous[], change_description
    - Crea Document + DocumentVersion (version 1) + permessi
    - Calcola checksum SHA256 del file
    - Crea entry AuditLog
  
  - update: PATCH /api/documents/{id}/
    - Aggiorna metadata del documento (title, description, folder, metadata_values)
    - NON aggiorna il file (usa upload_version per quello)
    - Solo chi ha can_write O ADMIN
  
  - destroy: DELETE /api/documents/{id}/
    - Soft delete
    - Solo chi ha can_delete O ADMIN
    - 400 se documento protocollato (quando implementato)
  
  Extra endpoints:
  
  POST /api/documents/{id}/upload_version/:
    - Carica nuova versione del file (multipart)
    - Campi: file, change_description
    - Crea nuovo DocumentVersion con version_number incrementato
    - Imposta is_current=True sulla nuova, False sulle precedenti
    - Aggiorna document.current_version e updated_at
    - Verifica document non sia locked da altro utente (RF-037)
    - Crea AuditLog
  
  GET /api/documents/{id}/download/:
    - Scarica la versione corrente
    - Query param `version=N` per scaricare versione specifica
    - Risponde con FileResponse e Content-Disposition: attachment
    - Registra download su AuditLog
  
  GET /api/documents/{id}/versions/:
    - Lista di tutte le versioni con: version_number, file_name, 
      file_size, created_by, created_at, change_description, is_current
  
  POST /api/documents/{id}/lock/:
    - Imposta locked_by=current_user, locked_at=now (RF-037)
    - 400 se già bloccato da altro utente
  
  POST /api/documents/{id}/unlock/:
    - Rimuove lock (solo chi ha bloccato O ADMIN)
  
  POST /api/documents/{id}/copy/:
    - Crea una copia del documento (RF-038)
    - Campi opzionali: new_title, folder_id
    - Copia il file fisicamente con nuovo nome
    - Risponde con il nuovo documento
  
  PATCH /api/documents/{id}/move/:
    - Sposta documento in altra cartella (RF-039)
    - Campo: folder_id (null = root)
  
  POST /api/documents/{id}/attachments/:
    - Upload allegato (RF-036)
    - Campo: file, description
  
  DELETE /api/documents/{id}/attachments/{att_id}/:
    - Rimuove allegato
  
  GET /api/documents/{id}/attachments/:
    - Lista allegati con download URL

Serializers:
  - DocumentListSerializer: campi base senza contenuto file
  - DocumentDetailSerializer: completo con versioni e allegati
  - DocumentCreateSerializer: con FileField
  - DocumentVersionSerializer
  - DocumentAttachmentSerializer

TEST `backend/apps/documents/tests/test_documents.py`:
  - Upload documento → versione 1 creata, file salvato, checksum calcolato
  - Upload nuova versione → versione 2, vecchia non è più current
  - Download versione corrente → file corretto
  - Download versione specifica con ?version=1
  - Lock documento → altro utente non può fare upload_version → 409
  - Unlock → upload di nuovo possibile
  - Copia documento → nuovo documento con stesso file
  - Spostamento cartella → folder aggiornata
  - Permessi: utente senza permesso → 403 su retrieve e download
  - Allegati: upload, lista, delete

Esegui: `pytest backend/apps/documents/ -v --tb=short`
```

---

## STEP 3.4 — Frontend: File Explorer e Upload

### Prompt per Cursor:

```
Crea l'interfaccia di gestione documenti nel frontend.

Aggiungi `frontend/src/services/documentService.ts`:
  - Tutte le chiamate API per documenti, cartelle, versioni, allegati
  - uploadDocument(data, onProgress): usa XMLHttpRequest per progress tracking
  - downloadDocument(id, version?): triggera download browser

Crea `frontend/src/components/documents/`:

FileExplorer.tsx:
  - Layout a due colonne: albero cartelle (sinistra) + lista documenti (destra)
  - Albero cartelle: cliccabile, espandibile, breadcrumb in cima
  - Lista documenti: tabella con colonne: nome, tipo, dimensione, versione, 
    stato, data modifica, autore, azioni
  - Double-click su documento → apre DocumentDetailPanel
  - Drag & drop per spostare documenti tra cartelle
  - Pulsanti: "Nuova Cartella", "Carica Documento"

FolderTree.tsx (usato in FileExplorer):
  - Albero ricorsivo delle cartelle
  - Icone per cartelle aperte/chiuse
  - Context menu: rinomina, elimina, nuova sottocartella
  - Indicatore di caricamento

DocumentTable.tsx:
  - Lista documenti nella cartella selezionata
  - Colonna stato con badge colorati (draft=grigio, in_review=arancio, 
    approved=verde, rejected=rosso, archived=nero)
  - Colonna versione
  - Azioni: download, nuova versione, copia, sposta, elimina
  - Selezione multipla per azioni batch

UploadModal.tsx:
  - Drag & drop area O selezione file
  - Campi: title (default: nome file), description, cartella
  - Selezione struttura metadati (preparazione Fase 4)
  - Progress bar durante upload
  - Gestione errori (file troppo grande, tipo non supportato)
  - Upload multiplo con lista file e progress individuale

DocumentDetailPanel.tsx:
  - Slide-over panel (lateral panel)
  - Info documento: titolo, descrizione, stato, versione attuale
  - Tab "Versioni": lista versioni con download per ciascuna
  - Tab "Allegati": lista + upload allegato
  - Tab "Permessi": chi può accedere (solo ADMIN)
  - Bottoni: modifica metadati, blocca/sblocca, nuova versione, download

DocumentLockBadge.tsx:
  - Badge "Bloccato da [nome]" se documento è locked
  - Se locked dal current user: bottone "Sblocca"

VersionHistoryModal.tsx:
  - Lista versioni con numero, data, autore, descrizione modifica
  - Download singola versione
  - Confronto visivo tra due versioni (solo metadata, non contenuto)

Crea `frontend/src/pages/DocumentsPage.tsx` (route: /documents):
  - FileExplorer come componente principale
  - Gestione URL: /documents?folder={id} per navigazione diretta

TEST Vitest:
  - FileExplorer: render, navigazione cartelle aggiorna lista
  - UploadModal: selezione file, validazione dimensione, submit
  - DocumentTable: render, filtri, sorting
  - DocumentDetailPanel: tabs, download trigger

Esegui: `npm run test -- --run` → tutti passano
Esegui: `npm run build` → nessun errore
```

---

## TEST INTEGRAZIONE FASE 3

### Prompt per Cursor:

```
Esegui i test di integrazione per la Fase 3.

1. `docker-compose exec backend pytest apps/documents/ -v --cov=apps/documents`
   → Coverage > 80%

2. `docker-compose exec frontend npm run test -- --run`
   → Tutti passano

3. Test manuale:
   a) Crea cartella "Contratti" come admin
   b) Crea sottocartella "2024" dentro "Contratti"
   c) Carica documento PDF (es. qualsiasi PDF) in "Contratti/2024"
      → Verifica: versione 1 creata, checksum nel DB
   d) Carica nuova versione dello stesso documento
      → Verifica: versione 2 è current, versione 1 disponibile nel history
   e) Download versione 1 → file corretto
   f) Download versione 2 (current) → file corretto
   g) Prova upload file > 200MB → errore appropriato
   h) Blocca documento come admin
      → Login come operatore → prova upload nuova versione → 409
   i) Sblocca come admin → operatore riesce a caricare
   j) Copia documento → nuovo documento nella stessa cartella
   k) Sposta documento in "Contratti" → non più in "2024"

4. Browser:
   - /documents mostra file explorer
   - Navigazione cartelle aggiorna lista documenti
   - Upload con progress bar funziona
   - Click su documento apre panel laterale
   - Versioni visibili nel panel

Crea `FASE_03_TEST_REPORT.md` con risultati.
```
