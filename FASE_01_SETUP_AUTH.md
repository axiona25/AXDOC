# AXDOC — FASE 01
# Setup Progetto, Autenticazione e Utenti Base

**Prerequisito:** nessuno — è la prima fase.

---

## CHECKLIST DI COMPLETAMENTO

Prima di passare alla FASE 02, verificare che TUTTI questi punti siano ✅:

- [ ] `docker-compose up --build` avvia backend, frontend, db e redis senza errori
- [ ] `python manage.py migrate` completa senza errori
- [ ] API `POST /api/auth/login/` restituisce JWT con credenziali valide
- [ ] API `POST /api/auth/login/` restituisce 401 con credenziali errate
- [ ] API `POST /api/auth/logout/` invalida il refresh token
- [ ] API `POST /api/auth/refresh/` rinnova l'access token
- [ ] Blocco account dopo 5 tentativi falliti → 423 (RF-005)
- [ ] Sblocco automatico dopo 15 minuti
- [ ] API `POST /api/auth/password-reset/` invia email con token (RF-003)
- [ ] API `POST /api/auth/password-reset/confirm/` reimposta password (RF-004)
- [ ] API `GET /api/users/me/` restituisce profilo utente autenticato
- [ ] API `GET /api/users/` funziona solo per ADMIN
- [ ] Registro `AuditLog` per ogni login/logout
- [ ] Tutti i test pytest passano (`pytest --cov` ≥ 80%)
- [ ] Frontend: pagina `/login` funzionante con gestione errori
- [ ] Frontend: pagina `/forgot-password` funzionante
- [ ] Frontend: pagina `/reset-password/:token` funzionante
- [ ] Frontend: routing protetto — redirect a `/login` se non autenticato
- [ ] Frontend: tutti i test Vitest passano
- [ ] `npm run build` completa senza errori TypeScript

---

Vedi i prompt degli STEP 1.1–1.4 e TEST INTEGRAZIONE nel documento originale della FASE 01.
