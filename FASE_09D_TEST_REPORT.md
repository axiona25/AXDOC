# FASE 09D (FASE 04) — Report test integrazione

## Implementazione completata

### STEP 9D.1 — Import utenti CSV/Excel (RF-017)
- **Backend:** `apps/users/importers.py` — `UserImporter` con `parse_file`, `validate_row`, `import_users`, `get_template_csv`, `get_template_xlsx`
- **API:** `GET /api/users/import/template/?format=csv|xlsx`, `POST /api/users/import/preview/`, `POST /api/users/import/`
- **Frontend:** `ImportUsersModal` (upload → preview → import), integrazione in `UsersPage` con pulsante "Importa utenti"
- **Test:** `backend/apps/users/tests/test_import.py`

### STEP 9D.2 — Gruppi utenti (RF-016)
- **Backend:** Modelli `UserGroup`, `UserGroupMembership` in `apps/users/models.py`
- **API:** `UserGroupViewSet` su `/api/groups/` — list, retrieve, create, update, destroy, `add_members`, `remove_member`, `members`
- **Frontend:** `GroupsPage` (route `/groups`), `groupService.ts`
- **Test:** `backend/apps/users/tests/test_groups.py`
- **Nota:** `DocumentGroupPermission` e assegnazione gruppi ai documenti saranno integrati in FASE 05 (documenti).

### STEP 9D.3 — Cifratura documenti on-demand
- **Backend:** App `documents` con `Document`, `DocumentVersion`; `documents/encryption.py` (AES-256-GCM, PBKDF2)
- **API:** `POST /api/documents/{id}/encrypt/`, `POST /api/documents/{id}/decrypt_download/`
- **Test:** `backend/apps/documents/tests/test_encryption.py`
- **Frontend:** Modali Encrypt/Decrypt e badge documenti cifrati da integrare in DocumentDetailPanel (FASE 05).

### STEP 9D.4 — Pannello gestione licenza
- **Backend:** App `admin_panel` — `SystemLicense` (singleton id=1), `GET /api/admin/license/`, `GET /api/admin/system_info/`, `LicenseCheckMiddleware`, comando `setup_license`
- **Frontend:** `LicensePage` (route `/admin/license`), `licenseService.ts`
- **Dashboard:** Link "Licenza" e "Gruppi" per ADMIN

## Come eseguire i test

```bash
# Backend (in Docker)
docker-compose exec backend python manage.py migrate
docker-compose exec backend pytest backend/apps/users/tests/test_import.py backend/apps/users/tests/test_groups.py backend/apps/documents/tests/test_encryption.py backend/apps/admin_panel/ -v --tb=short

# Frontend
cd frontend && npm run build
```

## Test manuali suggeriti

1. **Import:** Scarica template CSV, compila 2–3 righe, anteprima, importa con "Invia invito" attivo.
2. **Gruppi:** Crea gruppo da Admin Django, verifica lista in `/groups`; aggiungi membri via API o admin.
3. **Licenza:** `python manage.py setup_license --org-name "Test" --max-users 10`; apri `/admin/license`.
4. **Cifratura:** Crea documento con una versione file, chiama `POST /api/documents/{id}/encrypt/` con password; poi `POST .../decrypt_download/` con la stessa password per scaricare.
