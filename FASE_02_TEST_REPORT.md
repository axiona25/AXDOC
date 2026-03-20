# FASE 02 — Report test di integrazione

Eseguire i comandi sotto e compilare i risultati.

## 1. Backend

```bash
docker-compose exec backend pytest apps/organizations apps/authentication -v --tb=short
docker-compose exec backend pytest --cov=apps --cov-report=term-missing
```

- [ ] Tutti i test passano
- [ ] Coverage ≥ 80%

## 2. Frontend

```bash
docker-compose exec frontend npm run test -- --run
docker-compose exec frontend npm run build
```

- [ ] Tutti i test passano
- [ ] Build senza errori TypeScript

## 3. Test manuale E2E

- [ ] Creare UO "Direzione" (root) come admin
- [ ] Creare UO "IT" con parent "Direzione"
- [ ] GET /api/organizations/tree/ mostra gerarchia
- [ ] Invitare operatore@test.com come OPERATOR nell'UO "IT"
- [ ] Verificare email in console Django
- [ ] Accettare invito da link: nome, cognome, password
- [ ] Login con operatore@test.com
- [ ] Operatore non vede /users (403)
- [ ] Admin vede operatore in membri UO "IT"
- [ ] Export CSV UO "IT" scarica file con header e dati

## 4. Browser

- [ ] /organizations mostra albero UO
- [ ] Click su UO mostra membri
- [ ] Form invito funziona (email in console)
- [ ] /users mostra lista utenti con paginazione
