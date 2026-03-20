# AXDOC — Riferimento API

Base URL: `/api/`

## Autenticazione

| Metodo | Endpoint | Descrizione |
|--------|----------|-------------|
| POST | /api/auth/login/ | Login (email, password) → JWT |
| POST | /api/auth/logout/ | Logout (blacklist refresh) |
| GET | /api/auth/me/ | Utente corrente |
| POST | /api/auth/change-password/ | Cambio password |
| POST | /api/auth/password-reset/ | Richiesta reset password |
| POST | /api/auth/password-reset/confirm/ | Conferma reset (token, new_password) |
| POST | /api/auth/invite/ | Invito utente (ADMIN) |
| GET/POST | /api/auth/accept-invitation/\<token\>/ | Accetta invito |

## Documenti e cartelle

| Metodo | Endpoint | Descrizione |
|--------|----------|-------------|
| GET/POST | /api/documents/ | Lista, creazione |
| GET/PUT/PATCH/DELETE | /api/documents/\<id\>/ | Dettaglio, aggiornamento |
| GET/POST | /api/documents/\<id\>/versions/ | Versioni |
| POST | /api/documents/\<id\>/upload_version/ | Carica nuova versione |
| GET | /api/documents/\<id\>/download/ | Download file |
| GET/POST | /api/documents/\<id\>/share/ | Condivisione |
| POST | /api/documents/\<id\>/chat/ | Chat documento |
| GET/POST | /api/folders/ | Cartelle |

## Workflow

| Metodo | Endpoint | Descrizione |
|--------|----------|-------------|
| GET/POST | /api/workflows/templates/ | Template workflow |
| GET | /api/workflows/instances/ | Istanze |
| POST | /api/documents/\<id\>/start_workflow/ | Avvia workflow |
| POST | /api/documents/\<id\>/workflow_action/ | Azione (approva/rifiuta) |

## Protocolli e fascicoli

| Metodo | Endpoint | Descrizione |
|--------|----------|-------------|
| GET/POST | /api/protocols/ | Protocolli |
| GET/POST | /api/dossiers/ | Fascicoli |
| POST | /api/dossiers/\<id\>/chat/ | Chat fascicolo |

## Ricerca, notifiche, audit

| Metodo | Endpoint | Descrizione |
|--------|----------|-------------|
| GET | /api/search/?q= | Ricerca full-text |
| GET | /api/notifications/ | Notifiche utente |
| GET | /api/audit/ | Registro audit |
| GET | /api/audit/document/\<doc_id\>/ | Attività per documento |

## Dashboard

| Metodo | Endpoint | Descrizione |
|--------|----------|-------------|
| GET | /api/dashboard/stats/ | Statistiche (per ruolo) |
| GET | /api/dashboard/recent_documents/ | Ultimi documenti |
| GET | /api/dashboard/my_tasks/ | Step workflow assegnati |

## Chat

| Metodo | Endpoint | Descrizione |
|--------|----------|-------------|
| GET/POST | /api/chat/rooms/ | Room, creazione |
| POST | /api/chat/rooms/direct/ | Chat diretta (user_id) |
| GET/POST | /api/chat/rooms/\<id\>/messages/ | Messaggi |
| GET | /api/chat/rooms/unread_count/ | Conteggio non letti |
| POST | /api/chat/calls/initiate/ | Avvia videochiamata |
| GET | /api/chat/ice_servers/ | Server STUN/ICE |

WebSocket: `ws/chat/<room_id>/?token=<access_token>`, `ws/presence/`, `ws/call/<call_id>/`

## Utenti e organizzazioni (ADMIN)

| Metodo | Endpoint | Descrizione |
|--------|----------|-------------|
| GET/POST | /api/users/ | Utenti |
| GET/POST | /api/organizations/ | Unità organizzative |
| GET/POST | /api/groups/ | Gruppi |
| GET/POST | /api/metadata/structures/ | Strutture metadati |
