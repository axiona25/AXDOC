# AXDOC — FASE 02
# Gestione Utenti Avanzata e Unità Organizzative

**Prerequisito:** FASE 01 completata e tutti i test passanti.

---

## CHECKLIST DI COMPLETAMENTO

- [ ] API `/api/organizations/` CRUD completo
- [ ] Gerarchia UO (parent/children) funzionante
- [ ] Univocità codice UO (RF-027)
- [ ] Assegnazione utenti a UO con ruoli (RF-025)
- [ ] Invito utente via email con link di accettazione (RF-018)
- [ ] Utente invitato imposta password al primo accesso
- [ ] Export lista utenti UO in CSV (RF-026 collaudo)
- [ ] Filtro UO "Le mie" / "Tutte" funzionante
- [ ] Frontend: pagina Gestione Utenti (solo ADMIN)
- [ ] Frontend: pagina Unità Organizzative con albero gerarchico
- [ ] Frontend: form invito utente
- [ ] Tutti i test pytest passano
- [ ] Tutti i test React passano

---

## Implementazione

- **STEP 2.1** — App `organizations`: modelli `OrganizationalUnit`, `OrganizationalUnitMembership`; serializers; ViewSet con tree, add_member, remove_member, export CSV; test.
- **STEP 2.2** — Modello `UserInvitation`; `InviteUserView`, `AcceptInvitationView`; test inviti.
- **STEP 2.3** — Frontend: `userService`, `organizationService`; `UserTable`, `InviteUserModal`, `OUTree`, `OUFormModal`, `OUMembersPanel`; pagine `UsersPage`, `OrganizationsPage`, `AcceptInvitationPage`; route e navigazione.

Eseguire i test di integrazione e compilare `FASE_02_TEST_REPORT.md` con i risultati.
