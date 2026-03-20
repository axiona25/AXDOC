# AXDOC — FASE 08
# Workflow Documentale Multi-Step

## Obiettivo
Implementare il sistema di workflow approvativo multi-step
basato su ruoli RACI per i documenti.

**Prerequisito: FASE 06 completata e tutti i test passanti.**

---

## CHECKLIST DI COMPLETAMENTO

- [ ] CRUD workflow (RF-048..RF-050)
- [ ] Workflow multi-step con ruoli per step (RF-051, RF-052)
- [ ] Pubblicazione workflow (RF-050)
- [ ] Avvio workflow su documento (RF-053)
- [ ] Approvazione documento (RF-053)
- [ ] Rifiuto documento con motivazione (RF-054)
- [ ] Richiesta modifica (RF-055)
- [ ] Tracciamento stato workflow (RF-056)
- [ ] Notifiche workflow (RF-057) — integrazione con app notifications (Fase 7)
- [ ] Filtro workflow "I tuoi" / "Tutti" (collaudo)
- [ ] Verifica avanzamento workflow per tutti i ruoli (collaudo)
- [ ] Frontend: gestione workflow (solo ADMIN)
- [ ] Frontend: dashboard workflow per operatori/revisori/approvatori
- [ ] Tutti i test passano

---

## STEP 5.1 — App Workflows: Modelli

### Prompt per Cursor:

```
Crea `backend/apps/workflows/` per il sistema di workflow documentale.

Requisiti: RF-048..RF-057

Crea `backend/apps/workflows/models.py`:

STEP_ACTION = [
  ('review', 'Revisione'),
  ('approve', 'Approvazione'),
  ('sign', 'Firma'),
  ('acknowledge', 'Presa visione'),
]

STEP_ASSIGNEE_TYPE = [
  ('role', 'Ruolo globale'),
  ('ou_role', 'Ruolo in Unità Organizzativa'),
  ('specific_user', 'Utente specifico'),
  ('document_ou', 'UO del documento'),
]

WORKFLOW_INSTANCE_STATUS = [
  ('active', 'In corso'),
  ('completed', 'Completato'),
  ('rejected', 'Rifiutato'),
  ('cancelled', 'Annullato'),
]

STEP_INSTANCE_STATUS = [
  ('pending', 'In attesa'),
  ('in_progress', 'In lavorazione'),
  ('completed', 'Completato'),
  ('rejected', 'Rifiutato'),
  ('skipped', 'Saltato'),
]

class WorkflowTemplate(models.Model):
  - id: UUID primary key
  - name: CharField max 200
  - description: TextField blank=True
  - is_published: bool default False (RF-050)
  - created_by: FK User
  - created_at, updated_at: timestamps
  - is_deleted: bool default False
  
  Metodo: can_be_applied_to(document) → bool

class WorkflowStep(models.Model):
  - id: UUID primary key
  - template: FK WorkflowTemplate related_name='steps'
  - name: CharField max 200
  - order: IntegerField
  - action: CharField choices STEP_ACTION
  - assignee_type: CharField choices STEP_ASSIGNEE_TYPE
  - assignee_role: CharField null=True (se assignee_type='role': APPROVER, REVIEWER, ecc.)
  - assignee_user: FK User null=True (se assignee_type='specific_user')
  - assignee_ou: FK OrganizationalUnit null=True (se assignee_type='ou_role')
  - assignee_ou_role: CharField null=True
  - is_required: bool default True
  - deadline_days: IntegerField null=True (giorni per completare lo step)
  - instructions: TextField blank=True
  
  Meta: ordering = ['order']

class WorkflowInstance(models.Model):
  - id: UUID primary key
  - template: FK WorkflowTemplate
  - document: FK Document related_name='workflow_instances'
  - started_by: FK User
  - started_at: auto_now_add
  - completed_at: DateTimeField null=True
  - status: CharField choices WORKFLOW_INSTANCE_STATUS default 'active'
  - current_step_order: IntegerField default 0
  
  Metodo: get_current_step() → WorkflowStepInstance | None
  Metodo: advance() → avanza al prossimo step
  Metodo: get_assignees_for_step(step) → lista User assegnati

class WorkflowStepInstance(models.Model):
  - id: UUID primary key
  - workflow_instance: FK WorkflowInstance related_name='step_instances'
  - step: FK WorkflowStep
  - assigned_to: ManyToMany User (utenti assegnati a questo step)
  - status: CharField choices STEP_INSTANCE_STATUS default 'pending'
  - started_at: DateTimeField null=True
  - completed_at: DateTimeField null=True
  - completed_by: FK User null=True
  - action_taken: CharField null=True (approve/reject/request_changes)
  - comment: TextField blank=True
  - deadline: DateTimeField null=True
  
  Meta: unique_together = ['workflow_instance', 'step']

Crea migrations con `makemigrations workflows`
```

---

## STEP 5.2 — API Workflow

### Prompt per Cursor:

```
Crea le API per il workflow in `backend/apps/workflows/views.py`.

WorkflowTemplateViewSet:
  - list: tutti i workflow (query param `mine=true` → solo creati dall'utente)
    (RF-057 filtro collaudo)
  - retrieve: con steps
  - create: solo ADMIN
  - update: solo ADMIN, non modificabile se ha istanze attive
  - destroy: soft delete, 400 se ha istanze attive
  
  Extra:
  - POST /api/workflows/templates/{id}/publish/: pubblica workflow (ADMIN)
    → is_published = True, non modificabile dopo
  - POST /api/workflows/templates/{id}/unpublish/: solo ADMIN, solo se no istanze attive
  - GET /api/workflows/templates/{id}/steps/: lista step del template

WorkflowStepViewSet (nested sotto templates):
  - create: POST /api/workflows/templates/{tmpl_id}/steps/
  - update: PATCH .../{step_id}/
  - destroy: DELETE .../{step_id}/
  - Aggiorna automaticamente l'ordine degli altri step se necessario

WorkflowInstanceViewSet:
  - list: GET /api/workflows/instances/
    - Per ADMIN: tutti
    - Per altri utenti: istanze in cui sono assegnati come responsabili di step
    - Filtrabile: document_id, status, template_id
  - retrieve: dettaglio con step instances e history
  
  Extra (azioni sul documento — aggiunti a DocumentViewSet):
  
  POST /api/documents/{id}/start_workflow/:
    - Solo ADMIN o chi ha can_write
    - Corpo: {"template_id": "..."}
    - Verifica workflow pubblicato
    - Crea WorkflowInstance
    - Crea tutti i WorkflowStepInstance in status 'pending'
    - Attiva primo step: status → 'in_progress', calcola assigned_to
    - Aggiorna Document.status → 'in_review'
    - Invia notifica agli assegnati del primo step
    - 400 se documento già ha workflow attivo
  
  POST /api/documents/{id}/workflow_action/:
    - Richiede che l'utente sia assegnato allo step corrente
    - Corpo: {"action": "approve|reject|request_changes", "comment": "..."}
    
    Se action = 'approve':
      - Marca step corrente come completed
      - Se c'è prossimo step: avanza, notifica nuovi assegnati
      - Se era l'ultimo step: 
        → WorkflowInstance.status = 'completed'
        → Document.status = 'approved'
        → Notifica started_by
    
    Se action = 'reject':
      - Marca step come rejected (comment obbligatorio)
      - WorkflowInstance.status = 'rejected'
      - Document.status = 'rejected'
      - Notifica started_by con motivazione
    
    Se action = 'request_changes':
      - Marca step come 'in_progress' con commento
      - Document.status rimane 'in_review'
      - Notifica documento creator con commento (RF-055)
  
  GET /api/documents/{id}/workflow_history/:
    - Lista di tutti i WorkflowInstance del documento
    - Per ognuno: template, steps con azioni prese, date

Crea `backend/apps/workflows/services.py`:
  - WorkflowService.get_assignees(step, document) → lista User
    Logica: 
    - 'role' → tutti gli utenti con quel ruolo
    - 'specific_user' → l'utente specificato
    - 'ou_role' → utenti con quel ruolo nelle UO del documento
    - 'document_ou' → utenti nelle UO che hanno accesso al documento
  
  - WorkflowService.check_deadline_violations() → invia reminder per step scaduti
    (Da chiamare con cron/celery, per ora solo metodo)

TEST `backend/apps/workflows/tests/`:
  - CRUD template solo ADMIN
  - Pubblicazione workflow → non modificabile
  - Avvio workflow su documento: istanza creata, step attivato, assegnati corretti
  - Approve primo step: avanza al secondo
  - Approve ultimo step: documento diventa APPROVED
  - Reject: documento diventa REJECTED
  - Request changes: documento rimane IN_REVIEW, notifica creata
  - Utente non assegnato allo step → 403 su workflow_action
  - Filtro mine=true: solo workflow dell'utente

Esegui: `pytest backend/apps/workflows/ -v --tb=short`
```

---

## STEP 5.3 — Frontend: Workflow UI

### Prompt per Cursor:

```
Crea l'interfaccia workflow nel frontend.

Aggiungi `frontend/src/services/workflowService.ts`:
  - Tutti gli endpoint CRUD template e steps
  - startWorkflow(documentId, templateId)
  - workflowAction(documentId, action, comment)
  - getWorkflowHistory(documentId)
  - getMyWorkflowInstances(): istanze in cui l'utente deve agire

Crea `frontend/src/components/workflows/`:

WorkflowTemplateBuilder.tsx (solo ADMIN):
  - Lista step con drag & drop per riordinamento
  - Per ogni step: nome, azione (select), tipo assegnatario, assegnatario
  - Aggiungi step / Rimuovi step
  - Preview del flusso come stepper visivo

WorkflowStepperVisual.tsx:
  - Visualizzazione grafica del workflow come stepper orizzontale
  - Ogni step: icona azione, nome, assegnatario
  - Step corrente evidenziato
  - Step completati: verde con check; rifiutati: rosso; pending: grigio

WorkflowActionModal.tsx:
  - Modale per eseguire azione sullo step corrente
  - Select azione: Approva / Rifiuta / Richiedi modifiche
  - Campo commento (obbligatorio per Rifiuta)
  - Bottone conferma con loading state

DocumentWorkflowPanel.tsx (integra in DocumentDetailPanel):
  - Tab "Workflow" nel panel del documento
  - Se non c'è workflow attivo: bottone "Avvia Workflow" (select template)
  - Se c'è workflow attivo: WorkflowStepperVisual + stato corrente
  - Se l'utente è assegnato allo step corrente: bottone "Esegui Azione"
  - WorkflowHistory: accordion con tutte le istanze passate

WorkflowDashboard.tsx:
  - Lista step assegnati all'utente corrente
  - Ogni riga: titolo documento, nome step, azione richiesta, scadenza
  - Click → apre DocumentDetailPanel sul documento
  - Badge con numero di step pendenti

Crea pagine:
  
WorkflowsPage.tsx (route: /workflows, solo ADMIN):
  - Tabs: "I miei Workflow" / "Tutti i Workflow"
  - WorkflowTemplateTable con azioni: modifica, pubblica, elimina
  - Modal per creare/modificare con WorkflowTemplateBuilder

Aggiungi sezione "Da fare" nella Dashboard principale:
  - getMyWorkflowInstances() → mostra badge con count
  - Lista compatta dei task pendenti

TEST Vitest:
  - WorkflowTemplateBuilder: aggiunta/rimozione step
  - WorkflowStepperVisual: render con diversi stati
  - WorkflowActionModal: submit approve/reject

Esegui: `npm run test -- --run`
Esegui: `npm run build`
```

---

## TEST INTEGRAZIONE FASE 5

### Prompt per Cursor:

```
Test di integrazione Fase 5.

1. `pytest apps/workflows/ apps/documents/ -v --cov`

2. `npm run test -- --run`

3. Test manuale completo del ciclo approvativo:
   
   Setup:
   - Crea utenti: revisore@test.com (REVIEWER), approvatore@test.com (APPROVER)
   - Crea UO "Legal" con revisore e approvatore
   
   Workflow template:
   a) Crea template "Approvazione Standard" con 2 step:
      - Step 1: "Revisione" (action=review, assignee_type=role, role=REVIEWER)
      - Step 2: "Approvazione" (action=approve, assignee_type=role, role=APPROVER)
   b) Pubblica il template
   c) Verifica: template non modificabile dopo pubblicazione
   
   Ciclo completo - percorso positivo:
   d) Carica documento come admin
   e) Avvia workflow con template "Approvazione Standard"
      → documento status = IN_REVIEW
      → step 1 attivo, revisore è assignato
   f) Login come revisore, vai a /workflows
      → step 1 visibile come pending
   g) Approva step 1 → step 2 diventa attivo, approvatore notificato
   h) Login come approvatore
      → step 2 visibile
   i) Approva step 2 → documento status = APPROVED
   
   Ciclo - percorso negativo:
   j) Nuovo documento, avvia workflow
   k) Revisore → "Richiedi modifiche" con commento
      → documento rimane IN_REVIEW, admin riceve notifica
   l) Revisore → "Rifiuta" con motivazione
      → documento status = REJECTED, workflow chiuso
   
   m) GET /api/documents/{id}/workflow_history/ → mostra entrambe le istanze

4. Browser:
   - /workflows mostra template con builder
   - DocumentDetailPanel tab Workflow funziona
   - Badge "Da fare" in dashboard mostra step pendenti

Crea `FASE_05_TEST_REPORT.md`.
```
