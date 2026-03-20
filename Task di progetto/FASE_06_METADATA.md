# AXDOC — FASE 06
# Strutture Metadati Dinamiche

## Obiettivo
Implementare il sistema di strutture metadati personalizzabili
che definiscono le tipologie di documento e i campi associati.

**Prerequisito: FASE 05 completata e tutti i test passanti.**

---

## CHECKLIST DI COMPLETAMENTO

- [ ] CRUD strutture metadati (RF-040..RF-042)
- [ ] Campi: testo, numero, data, booleano, select, multi-select, email, telefono (RF-045)
- [ ] Validazione campi obbligatori (RF-044)
- [ ] Associazione struttura a documento (RF-043)
- [ ] Preview struttura con lista documenti associati (collaudo)
- [ ] Ricerca documenti per metadati (RF-046)
- [ ] Template documentale (RF-047) — stub per integrazione future
- [ ] Filtri per struttura metadati nella lista documenti
- [ ] Frontend: form dinamico per metadati
- [ ] Tutti i test passano

---

## STEP 4.1 — App Metadata: Modelli e API

### Prompt per Cursor:

```
Crea `backend/apps/metadata/` per la gestione delle strutture metadati.

Requisiti: RF-040..RF-047

Crea `backend/apps/metadata/models.py`:

FIELD_TYPES = [
  ('text', 'Testo libero'),
  ('number', 'Numero'),
  ('date', 'Data'),
  ('datetime', 'Data e ora'),
  ('boolean', 'Sì/No'),
  ('select', 'Selezione singola'),
  ('multiselect', 'Selezione multipla'),
  ('email', 'Email'),
  ('phone', 'Telefono'),
  ('textarea', 'Testo lungo'),
  ('url', 'URL'),
]

class MetadataStructure(models.Model):
  - id: UUID primary key
  - name: CharField max 200, unique
  - description: TextField blank=True
  - allowed_file_extensions: JSONField default=list
    (es: [".pdf", ".docx", ".xlsx"] — vuoto = tutti)
  - allowed_organizational_units: ManyToMany OrganizationalUnit
    (UO che possono usare questa struttura — vuoto = tutti)
  - is_active: bool default True
  - created_by: FK User
  - created_at, updated_at: timestamps
  
  Metodo: validate_metadata(values: dict) → lista errori di validazione

class MetadataField(models.Model):
  - id: UUID primary key
  - structure: FK MetadataStructure related_name='fields'
  - name: CharField max 200 (nome tecnico, snake_case)
  - label: CharField max 200 (etichetta UI)
  - field_type: CharField choices FIELD_TYPES
  - is_required: bool default False
  - is_searchable: bool default True (RF-046)
  - order: IntegerField default 0 (ordinamento nel form)
  - options: JSONField default=list 
    (per select/multiselect: [{"value": "v1", "label": "Label 1"}, ...])
  - default_value: JSONField null=True
  - validation_rules: JSONField default=dict
    (es: {"min": 0, "max": 100} per number; {"regex": "..."} per text)
  - help_text: CharField blank=True
  
  Meta: unique_together = ['structure', 'name']
        ordering = ['order', 'name']

Crea `backend/apps/metadata/serializers.py`:
  - MetadataFieldSerializer
  - MetadataStructureListSerializer: senza campi dettaglio
  - MetadataStructureDetailSerializer: con fields
  - MetadataStructureCreateSerializer: con fields nested (write)

Crea `backend/apps/metadata/views.py`:

MetadataStructureViewSet:
  - list: GET /api/metadata/structures/
    - Filtrabile per is_active, allowed_ous
    - Query param `usable_by_me=true` → strutture usabili dall'utente 
      (UO dell'utente inclusa nelle allowed_ous O allowed_ous vuoto)
  - retrieve: con fields e conteggio documenti associati
  - create: solo ADMIN
  - update: solo ADMIN — valida che i campi non cambino tipo se ci sono documenti
  - destroy: soft delete, 400 se ha documenti associati
  
  Extra:
  - GET /api/metadata/structures/{id}/documents/: lista documenti con questa struttura
  - POST /api/metadata/structures/{id}/validate/: 
    accetta `{"values": {...}}` e risponde con eventuali errori di validazione

Crea `backend/apps/metadata/validators.py`:
  - validate_metadata_values(structure, values) → dict di errori per campo
  - Implementa: required, min/max per numeri, regex per testo, 
    opzioni valide per select

Modifica `backend/apps/documents/models.py`:
  - Il campo metadata_values su Document ora viene validato
  - Aggiungi metodo Document.validate_metadata() che chiama metadata validators

Aggiungi endpoint a DocumentViewSet:
  - PATCH /api/documents/{id}/metadata/ → aggiorna solo metadata_values
    con validazione automatica tramite la struttura associata

Aggiorna migrations con `makemigrations metadata`

TEST `backend/apps/metadata/tests/`:
  - CRUD strutture solo ADMIN
  - Creazione struttura con campi di tutti i tipi
  - validate_metadata: campo required mancante → errore
  - validate_metadata: select con valore non in options → errore  
  - validate_metadata: number fuori range → errore
  - validate_metadata: campi validi → nessun errore
  - usable_by_me: filtra correttamente per UO
  - Aggiornamento tipo campo con documenti esistenti → 400

Esegui: `pytest backend/apps/metadata/ -v --tb=short`
Esegui: `pytest backend/apps/documents/ -v --tb=short` (regressione)
```

---

## STEP 4.2 — Frontend: Form Dinamico Metadati

### Prompt per Cursor:

```
Implementa il form dinamico per i metadati nel frontend.

Crea `frontend/src/services/metadataService.ts`:
  - getMetadataStructures(params): lista strutture
  - getMetadataStructure(id): dettaglio con campi
  - createMetadataStructure(data): crea struttura
  - updateMetadataStructure(id, data): modifica
  - deleteMetadataStructure(id): elimina
  - validateMetadata(structureId, values): valida valori

Crea `frontend/src/types/metadata.ts`:
  - MetadataFieldType (enum di tutti i tipi)
  - MetadataField, MetadataStructure
  - MetadataValues (Record<string, unknown>)

Crea `frontend/src/components/metadata/`:

DynamicMetadataForm.tsx:
  - Riceve: structure (MetadataStructure), values (MetadataValues), onChange
  - Renderizza campi dinamicamente in base a field_type:
    * text → <input type="text">
    * number → <input type="number"> con min/max da validation_rules
    * date → <input type="date">
    * datetime → <input type="datetime-local">
    * boolean → <Toggle> / checkbox
    * select → <Select> con options della struttura
    * multiselect → <MultiSelect> con options
    * email → <input type="email">
    * phone → <input type="tel">
    * textarea → <textarea>
    * url → <input type="url">
  - Mostra asterisco (*) per campi required
  - Mostra help_text sotto il campo
  - Mostra errori di validazione inline
  - Ordine campi secondo field.order

MetadataStructureForm.tsx (solo ADMIN):
  - Form per creare/modificare una struttura
  - Sezione info generali: name, description, allowed_file_extensions
  - Sezione campi: lista ordinabile dei campi (drag & drop)
  - Per ogni campo: label, name (auto-generato), type, required, searchable, 
    order, help_text
  - Per select/multiselect: editor delle options (aggiungi/rimuovi opzioni)
  - Per number: min/max
  - Preview live del form che verrà generato

MetadataStructureTable.tsx:
  - Tabella strutture con: nome, campi (count), documenti (count), stato
  - Azioni: modifica, anteprima, elimina
  - Filtri: attive/inattive

MetadataPreviewModal.tsx:
  - Mostra il form che gli utenti vedranno per questa struttura
  - Lista documenti associati alla struttura

Modifica `UploadModal.tsx` (da Fase 3):
  - Dopo selezione file: se l'estensione corrisponde a strutture, 
    mostra select "Tipo documento"
  - Dopo selezione struttura: mostra DynamicMetadataForm inline
  - Submit include metadata_values validati

Modifica `DocumentDetailPanel.tsx` (da Fase 3):
  - Tab "Metadati": mostra valori metadati in sola lettura con etichette
  - Se utente ha can_write: bottone "Modifica metadati" → form editabile

Crea `frontend/src/pages/MetadataPage.tsx` (route: /metadata, solo ADMIN):
  - MetadataStructureTable
  - Modal per creare/modificare struttura

TEST Vitest:
  - DynamicMetadataForm: render tutti i tipi di campo
  - DynamicMetadataForm: errori di validazione mostrati
  - MetadataStructureForm: aggiunta/rimozione campi
  - MetadataStructureForm: submit dati strutturati

Esegui: `npm run test -- --run`
Esegui: `npm run build`
```

---

## TEST INTEGRAZIONE FASE 4

### Prompt per Cursor:

```
Test di integrazione Fase 4.

1. `docker-compose exec backend pytest apps/metadata/ apps/documents/ -v --cov`

2. `docker-compose exec frontend npm run test -- --run`

3. Test manuale:
   a) Crea struttura "Contratto" con campi:
      - "fornitore" (testo, obbligatorio)
      - "valore_contratto" (numero, min=0)
      - "data_stipula" (data, obbligatoria)
      - "tipologia" (select, options: ["Fornitura", "Servizi", "Consulenza"])
      - "rinnovabile" (boolean)
   
   b) Carica documento con struttura "Contratto"
      → Lascia "fornitore" vuoto → errore validazione
      → Completa tutti i campi → documento creato con metadata_values
   
   c) Modifica metadati dal DocumentDetailPanel
      → Campo required vuoto → errore
      → Dati validi → aggiornamento
   
   d) GET /api/metadata/structures/{id}/documents/ 
      → mostra il documento creato al punto b)
   
   e) POST /api/metadata/structures/{id}/validate/ 
      con {"values": {"fornitore": "", "valore_contratto": -10}}
      → risponde con errori per entrambi i campi

4. Browser:
   - /metadata mostra tabella strutture
   - Form creazione struttura con campi drag & drop
   - Upload documento mostra form metadati corretto
   - Panel documento mostra metadati in sola lettura

Crea `FASE_04_TEST_REPORT.md`.
```
