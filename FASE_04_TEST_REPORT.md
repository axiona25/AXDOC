# FASE 04 — Test Report (Strutture Metadati Dinamiche)

Report dei test di integrazione per la Fase 4 (Strutture Metadati Dinamiche — FASE 06 nel numerale completo).

## 1. Test automatici Backend

```bash
docker-compose exec backend pytest apps/metadata/ apps/documents/ -v --tb=short
```

**Risultato:** 34 test passati

- **apps/metadata/** (14 test): modelli, validazione (required, select, number range), CRUD strutture (solo ADMIN), endpoint validate, usable_by_me, destroy con documenti → 400, update tipo campo con documenti → 400.
- **apps/documents/** (20 test): regressione documenti e cartelle (upload, versioni, download, lock, copy, move, permessi, allegati, encryption).

## 2. Test automatici Frontend

```bash
npm run test -- --run
```

**Risultato:** 24 test passati

- **DynamicMetadataForm**: render di tutti i tipi di campo, asterisco required, errori di validazione, onChange.
- **MetadataStructureForm**: campi nome/descrizione, pulsante “Aggiungi campo”, submit con dati strutturati.
- **UploadModal, DocumentTable, DocumentDetailPanel, FileExplorer**: invariati e passanti.

## 3. Build Frontend

```bash
npm run build
```

**Risultato:** Build completata senza errori.

## 4. Test manuali suggeriti

1. **Struttura “Contratto”**
   - Creare struttura con campi: fornitore (testo, obbligatorio), valore_contratto (numero, min=0), data_stipula (data, obbligatoria), tipologia (select: Fornitura, Servizi, Consulenza), rinnovabile (boolean).

2. **Upload con struttura**
   - Caricare documento con struttura “Contratto”: fornitore vuoto → errore validazione; tutti i campi compilati → documento creato con `metadata_values`.

3. **Modifica metadati**
   - Da DocumentDetailPanel → tab Metadati: modifica, campo obbligatorio vuoto → errore; dati validi → aggiornamento.

4. **API**
   - `GET /api/metadata/structures/{id}/documents/` → elenco documenti con quella struttura.
   - `POST /api/metadata/structures/{id}/validate/` con `{"values": {"fornitore": "", "valore_contratto": -10}}` → errori per entrambi i campi.

5. **Browser**
   - `/metadata`: tabella strutture, filtri, creazione/modifica/anteprima/eliminazione.
   - Upload documento: select “Tipo documento” e form metadati dinamico.
   - Dettaglio documento: tab Metadati in sola lettura e “Modifica metadati” (se can_write).

## Checklist completamento

- [x] CRUD strutture metadati (RF-040..RF-042)
- [x] Campi: testo, numero, data, datetime, boolean, select, multi-select, email, telefono, textarea, url (RF-045)
- [x] Validazione campi obbligatori (RF-044)
- [x] Associazione struttura a documento (RF-043)
- [x] Preview struttura con lista documenti associati
- [x] Ricerca documenti per metadati (RF-046) — filtro `metadata_structure_id` in lista documenti
- [x] Template documentale (RF-047) — stub per integrazioni future (struttura + campi)
- [x] Filtri per struttura metadati nella lista documenti
- [x] Frontend: form dinamico per metadati
- [x] Tutti i test passano
