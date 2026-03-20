# FASE 03 — Report test di integrazione

**Data esecuzione:** 2025-03-10  
**Riferimento:** Test di integrazione Fase 3 (documenti / cartelle / versioning).

---

## 1. Test backend — `apps/documents/`

**Comando eseguito:**
```bash
docker-compose exec backend pytest apps/documents/ -v --cov=apps/documents
```

**Risultato:** ✅ **Tutti passati**

| Test | Esito |
|------|--------|
| `DocumentEncryptionTest::test_decrypt_wrong_password_raises` | PASSED |
| `DocumentEncryptionTest::test_encrypt_decrypt_roundtrip` | PASSED |
| `DocumentEncryptAPITest::test_encrypt_creates_new_version` | PASSED |

**Coverage:** **82%** (> 80% richiesto) ✅

| Modulo | Stmts | Miss | Cover |
|--------|-------|------|--------|
| documents/__init__.py | 0 | 0 | 100% |
| documents/admin.py | 8 | 0 | 100% |
| documents/encryption.py | 33 | 0 | 100% |
| documents/models.py | 32 | 2 | 94% |
| documents/views.py | 77 | 35 | 55% |
| documents/tests/test_encryption.py | 54 | 2 | 96% |
| **TOTAL** | **218** | **39** | **82%** |

---

## 2. Test frontend

**Comando eseguito:**
```bash
docker-compose exec frontend npm run test -- --run
```

**Risultato:** ✅ **Tutti passati**

- **Test Files:** 3 passed  
- **Tests:** 9 passed  
- File: `ProtectedRoute.test.tsx`, `authStore.test.ts`, `LoginPage.test.tsx`  

*(In ambiente Docker compaiono warning React Router su future flag e errori di rete in stderr per le chiamate mock; i test risultano comunque passed.)*

---

## 3. Test manuali (a–k) — cartelle, upload, versioni, lock, copy, sposta

**Stato:** ⚠️ **Non eseguibili con il codice attuale**

I punti (a)–(k) e i controlli browser che hai indicato presuppongono l’implementazione completa della **gestione documenti con cartelle** (FASE 05 nell’indice):

- Cartelle (es. "Contratti", "2024") e gerarchia
- Upload PDF con creazione versione 1 e checksum
- Nuova versione dello stesso documento (versione 2, history)
- Download per versione (v1, v2)
- Limite upload 200 MB con errore appropriato
- Blocco documento (lock) → operatore riceve 409 su upload
- Sblocco → operatore può caricare
- Copia documento (nuovo documento in stessa cartella)
- Sposta documento (es. da "2024" a "Contratti")
- UI: `/documents` con file explorer, navigazione cartelle, progress bar upload, panel laterale con versioni

**Stato attuale dell’app `documents`:**

- Modelli: `Document`, `DocumentVersion` (senza cartelle, senza checksum, senza lock)
- API: `POST /api/documents/{id}/encrypt/`, `POST /api/documents/{id}/decrypt_download/` (solo cifratura on-demand)
- Nessun modello `Folder`, nessun endpoint di upload/download versioni, lock, copy, sposta
- Frontend: nessuna route `/documents` né pagina con file explorer

Per eseguire i test manuali (a)–(k) e i controlli browser è quindi necessario implementare la **FASE 05 — Documenti, cartelle, upload, versioning, lock** (e relative API e UI).

---

## 4. Browser — `/documents` e file explorer

**Stato:** ⚠️ **Non implementato**

- La route `/documents` non è definita in `App.tsx`.
- Non esiste una pagina “Documenti” con file explorer, navigazione cartelle, upload con progress bar o panel laterale versioni.

Tali funzionalità fanno parte della FASE 05 e andranno implementate lì.

---

## Riepilogo

| Verifica | Esito | Note |
|----------|--------|------|
| Backend `pytest apps/documents/` | ✅ Pass | 3 test, coverage 82% |
| Frontend `npm run test -- --run` | ✅ Pass | 9 test in 3 file |
| Coverage documents > 80% | ✅ Sì | 82% |
| Test manuali (a)–(k) | ⚠️ N/D | Richiedono FASE 05 (cartelle, upload, versioning, lock, copy, sposta) |
| Browser `/documents` e file explorer | ⚠️ N/D | Da implementare in FASE 05 |

**Conclusione:**  
Test automatici backend (documents) e frontend sono **passati** e la coverage sull’app `documents` è **> 80%**. I test manuali e i controlli browser che hai descritto sono da eseguire dopo l’implementazione della **FASE 05 — Documenti** (cartelle, upload, versioning, lock, copy, sposta e UI documenti).
