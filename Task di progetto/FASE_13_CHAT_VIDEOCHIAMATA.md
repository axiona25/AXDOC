# AXDOC — FASE 13
# Chat Real-Time e Videochiamata WebRTC

## Fonte nei documenti di analisi
AXDOC.docx — sezione "Chat e videochiamata":
> "Per coordinare le attività su documenti, fascicoli e protocolli è prevista 
> una funzionalità di chat e videochiamata 1-to-1 e di gruppo."

Documento Tecnico vDocs — sezione "Streaming Audio/Video":
> "2.4 Streaming Audio/Video" (citato nell'architettura come componente dedicato)

**Questa funzionalità è completamente assente in tutte le fasi precedenti.**

**Prerequisito: FASE 12 completata e tutti i test passanti.**

---

## CHECKLIST DI COMPLETAMENTO

- [ ] Chat 1-to-1 tra utenti interni
- [ ] Chat di gruppo (legata a documento, fascicolo o protocollo)
- [ ] Messaggi in tempo reale (WebSocket Django Channels)
- [ ] Storico messaggi persistente
- [ ] Indicatore di presenza (online/offline)
- [ ] Messaggi letti/non letti
- [ ] Allegati in chat (file, immagini)
- [ ] Videochiamata 1-to-1 (WebRTC peer-to-peer)
- [ ] Videochiamata di gruppo (WebRTC con SFU o mesh)
- [ ] Contesto documento: apertura chat dal DocumentDetailPanel
- [ ] Frontend: pannello chat laterale
- [ ] Frontend: UI videochiamata
- [ ] Tutti i test passano

---

## STEP 9C.1 — Setup Django Channels (WebSocket)

### Prompt per Cursor:

```
Configura Django Channels per WebSocket in tempo reale.

Installa in requirements.txt:
  - channels==4.0.*
  - channels-redis==4.2.*
  - daphne==4.0.*

Aggiungi in `backend/config/settings/base.py`:

INSTALLED_APPS += ['channels', 'daphne']

ASGI_APPLICATION = 'config.asgi.application'

CHANNEL_LAYERS = {
  'default': {
    'BACKEND': 'channels_redis.core.RedisChannelLayer',
    'CONFIG': {
      'hosts': [env('REDIS_URL', default='redis://redis:6379/0')],
    },
  },
}

Crea `backend/config/asgi.py`:
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
import apps.chat.routing

application = ProtocolTypeRouter({
  'http': django_asgi_app,
  'websocket': AllowedHostsOriginValidator(
    AuthMiddlewareStack(
      URLRouter(apps.chat.routing.websocket_urlpatterns)
    )
  ),
})

Aggiungi servizio Redis in `docker-compose.yml`:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

Aggiorna backend service in docker-compose.yml:
  - Usa daphne invece di runserver per supporto ASGI:
    command: daphne -b 0.0.0.0 -p 8000 config.asgi:application

Aggiorna requirements.txt: aggiungi anche `redis==5.*`

TEST: verifica che `docker-compose up` avvii correttamente con daphne.
  `curl http://localhost:8000/api/auth/login/` → deve rispondere normalmente
```

---

## STEP 9C.2 — App Chat: Modelli e WebSocket

### Prompt per Cursor:

```
Crea `backend/apps/chat/` per il sistema di messaggistica.

Crea `backend/apps/chat/models.py`:

ROOM_TYPE = [
  ('direct', 'Chat diretta 1-to-1'),
  ('group', 'Chat di gruppo'),
  ('document', 'Chat documento'),
  ('dossier', 'Chat fascicolo'),
  ('protocol', 'Chat protocollo'),
]

class ChatRoom(models.Model):
  - id: UUID primary key
  - room_type: CharField choices ROOM_TYPE
  - name: CharField blank=True (per group, document, dossier)
  - members: ManyToMany User through ChatMembership
  
  # Contesto (solo uno dei tre sarà non null)
  - document: FK Document null=True related_name='chat_room'
  - dossier: FK Dossier null=True related_name='chat_room'
  - protocol: FK Protocol null=True related_name='chat_room'
  
  - created_by: FK User null=True
  - created_at: auto_now_add
  - is_active: bool default True
  
  Metodo: get_or_create_direct(user1, user2):
    Trova O crea chat diretta tra due utenti
  
  Metodo: get_or_create_for_document(document):
    Trova O crea chat per documento

class ChatMembership(models.Model):
  - room: FK ChatRoom
  - user: FK User
  - joined_at: auto_now_add
  - last_read_at: DateTimeField null=True
  - is_admin: bool default False
  - notifications_enabled: bool default True
  Meta: unique_together = ['room', 'user']

class ChatMessage(models.Model):
  MESSAGE_TYPE = [
    ('text', 'Testo'),
    ('file', 'File'),
    ('image', 'Immagine'),
    ('system', 'Sistema'),  # es: "Mario ha aperto il documento"
  ]
  
  - id: UUID primary key
  - room: FK ChatRoom related_name='messages'
  - sender: FK User null=True (null per messaggi di sistema)
  - message_type: CharField choices MESSAGE_TYPE default='text'
  - content: TextField blank=True (testo del messaggio)
  - file: FileField upload_to='chat_files/%Y/%m/' null=True
  - file_name: CharField blank=True
  - file_size: IntegerField null=True
  - image: ImageField upload_to='chat_images/%Y/%m/' null=True
  - sent_at: auto_now_add
  - edited_at: DateTimeField null=True
  - is_deleted: bool default False
  - reply_to: FK self null=True (risposta a messaggio)
  
  Meta: ordering = ['sent_at']

class UserPresence(models.Model):
  """Traccia lo stato online degli utenti"""
  - user: OneToOne User
  - is_online: bool default False
  - last_seen: auto_now
  - current_room: FK ChatRoom null=True

Crea `backend/apps/chat/consumers.py` — WebSocket Consumer:

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

class ChatConsumer(AsyncWebsocketConsumer):
  
  async def connect(self):
    # Autenticazione: JWT dal query param o header
    user = await self.authenticate()
    if not user:
      await self.close(code=4001)
      return
    
    self.user = user
    self.room_id = self.scope['url_route']['kwargs']['room_id']
    self.room_group_name = f'chat_{self.room_id}'
    
    # Verifica membership
    if not await self.user_in_room(user, self.room_id):
      await self.close(code=4003)
      return
    
    # Unisciti al gruppo
    await self.channel_layer.group_add(self.room_group_name, self.channel_name)
    await self.accept()
    
    # Aggiorna presenza
    await self.set_online(user, self.room_id)
    
    # Notifica altri utenti della presenza
    await self.channel_layer.group_send(
      self.room_group_name,
      {'type': 'user_joined', 'user_id': str(user.id), 'user_name': user.get_full_name()}
    )
  
  async def disconnect(self, close_code):
    if hasattr(self, 'user'):
      await self.set_offline(self.user)
      await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
  
  async def receive(self, text_data):
    data = json.loads(text_data)
    action = data.get('type')
    
    if action == 'chat_message':
      message = await self.save_message(
        self.user, self.room_id, 
        data.get('content'), 
        data.get('reply_to')
      )
      await self.channel_layer.group_send(
        self.room_group_name,
        {
          'type': 'chat_message',
          'message_id': str(message.id),
          'content': message.content,
          'sender_id': str(self.user.id),
          'sender_name': self.user.get_full_name(),
          'sent_at': message.sent_at.isoformat(),
          'reply_to': data.get('reply_to'),
        }
      )
    
    elif action == 'typing':
      await self.channel_layer.group_send(
        self.room_group_name,
        {'type': 'typing', 'user_id': str(self.user.id), 'user_name': self.user.get_full_name()}
      )
    
    elif action == 'mark_read':
      await self.update_last_read(self.user, self.room_id)
  
  # Handler messaggi in arrivo dal gruppo
  async def chat_message(self, event):
    await self.send(text_data=json.dumps({'type': 'chat_message', **event}))
  
  async def typing(self, event):
    if event['user_id'] != str(self.user.id):  # non mandare a chi sta digitando
      await self.send(text_data=json.dumps({'type': 'typing', **event}))
  
  async def user_joined(self, event):
    await self.send(text_data=json.dumps({'type': 'user_joined', **event}))
  
  # Helper DB (async)
  @database_sync_to_async
  def authenticate(self): ...
  @database_sync_to_async
  def user_in_room(self, user, room_id): ...
  @database_sync_to_async
  def save_message(self, user, room_id, content, reply_to): ...
  @database_sync_to_async
  def set_online(self, user, room_id): ...
  @database_sync_to_async
  def set_offline(self, user): ...
  @database_sync_to_async
  def update_last_read(self, user, room_id): ...

class PresenceConsumer(AsyncWebsocketConsumer):
  """WebSocket globale per presenza utente (online/offline)"""
  
  async def connect(self):
    user = await self.authenticate()
    if not user:
      await self.close()
      return
    self.user = user
    await self.channel_layer.group_add('presence', self.channel_name)
    await self.accept()
    await self.set_online(user)
    await self.channel_layer.group_send('presence', {
      'type': 'user_online', 'user_id': str(user.id)
    })
  
  async def disconnect(self, close_code):
    if hasattr(self, 'user'):
      await self.set_offline(self.user)
      await self.channel_layer.group_send('presence', {
        'type': 'user_offline', 'user_id': str(self.user.id)
      })
      await self.channel_layer.group_discard('presence', self.channel_name)
  
  async def user_online(self, event):
    await self.send(text_data=json.dumps(event))
  
  async def user_offline(self, event):
    await self.send(text_data=json.dumps(event))

Crea `backend/apps/chat/routing.py`:
  websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<room_id>[0-9a-f-]+)/$', ChatConsumer.as_asgi()),
    re_path(r'ws/presence/$', PresenceConsumer.as_asgi()),
  ]

Crea `backend/apps/chat/views.py` — REST API:

ChatRoomViewSet:
  GET /api/chat/rooms/: lista room dell'utente con ultimo messaggio + unread count
  POST /api/chat/rooms/direct/: crea/recupera chat diretta con {user_id}
  POST /api/chat/rooms/: crea chat di gruppo con {name, member_ids}
  GET /api/chat/rooms/{id}/messages/: storico messaggi (paginato, 50 per pagina)
  POST /api/chat/rooms/{id}/messages/: invio messaggio REST (fallback senza WS)
  POST /api/chat/rooms/{id}/upload/: upload file/immagine in chat
  DELETE /api/chat/messages/{id}/: cancella messaggio (soft, solo sender)
  GET /api/chat/rooms/{id}/members/: lista membri con presenza
  POST /api/chat/rooms/{id}/add_member/: aggiunge membro (solo admin room)
  GET /api/chat/unread_count/: totale messaggi non letti in tutte le room

Endpoint contesto documento/fascicolo/protocollo:
  POST /api/documents/{id}/chat/: crea/recupera chat per documento
  POST /api/dossiers/{id}/chat/: crea/recupera chat per fascicolo

Crea `backend/apps/chat/serializers.py`:
  - ChatRoomSerializer (con last_message, unread_count, members)
  - ChatMessageSerializer
  - ChatMembershipSerializer (con UserPresence)

TEST `backend/apps/chat/tests/`:
  - Crea room diretta tra utente A e B → stessa room se chiamato due volte
  - Invia messaggio REST → appare nel GET messages
  - Unread count: messaggio non letto → count=1, dopo mark_read → count=0
  - Soft delete messaggio → non appare nella lista
  - Chat per documento: crea room legata al documento

Esegui: `pytest backend/apps/chat/ -v --tb=short`
```

---

## STEP 9C.3 — Videochiamata WebRTC

### Prompt per Cursor:

```
Implementa la segnalazione WebRTC per le videochiamate tramite Django Channels.

WebRTC funziona peer-to-peer: il backend gestisce solo la segnalazione 
(scambio SDP offer/answer e ICE candidates). I media fluiscono direttamente 
tra i browser senza passare dal server.

Crea `backend/apps/chat/call_consumer.py`:

class CallConsumer(AsyncWebsocketConsumer):
  """
  Gestisce la segnalazione WebRTC per videochiamate.
  Ogni chiamata ha un call_id univoco; tutti i partecipanti si uniscono
  allo stesso gruppo WebSocket per scambiarsi i messaggi di segnalazione.
  """
  
  async def connect(self):
    user = await self.authenticate()
    if not user:
      await self.close(code=4001)
      return
    
    self.user = user
    self.call_id = self.scope['url_route']['kwargs']['call_id']
    self.call_group = f'call_{self.call_id}'
    
    await self.channel_layer.group_add(self.call_group, self.channel_name)
    await self.accept()
    
    # Notifica altri partecipanti
    await self.channel_layer.group_send(self.call_group, {
      'type': 'participant_joined',
      'user_id': str(user.id),
      'user_name': user.get_full_name(),
    })
  
  async def disconnect(self, close_code):
    if hasattr(self, 'user'):
      await self.channel_layer.group_send(self.call_group, {
        'type': 'participant_left',
        'user_id': str(self.user.id),
      })
      await self.channel_layer.group_discard(self.call_group, self.channel_name)
  
  async def receive(self, text_data):
    data = json.loads(text_data)
    msg_type = data.get('type')
    target_user_id = data.get('target_user_id')  # per messaggi 1-to-1
    
    # Inoltra tutti i messaggi WebRTC al gruppo (o al target specifico)
    # Tipi gestiti: offer, answer, ice_candidate, call_ended
    payload = {
      'type': msg_type,
      'from_user_id': str(self.user.id),
      'from_user_name': self.user.get_full_name(),
      **{k: v for k, v in data.items() if k not in ['type', 'target_user_id']}
    }
    await self.channel_layer.group_send(self.call_group, payload)
  
  # Handler per ogni tipo di messaggio
  async def offer(self, event): await self.send_if_not_sender(event)
  async def answer(self, event): await self.send_if_not_sender(event)
  async def ice_candidate(self, event): await self.send_if_not_sender(event)
  async def call_ended(self, event): await self.send(text_data=json.dumps(event))
  async def participant_joined(self, event): await self.send(text_data=json.dumps(event))
  async def participant_left(self, event): await self.send(text_data=json.dumps(event))
  
  async def send_if_not_sender(self, event):
    if event.get('from_user_id') != str(self.user.id):
      await self.send(text_data=json.dumps(event))

Aggiungi in `backend/apps/chat/routing.py`:
  re_path(r'ws/call/(?P<call_id>[0-9a-f-]+)/$', CallConsumer.as_asgi()),

Aggiungi API REST per gestione chiamate:
  POST /api/chat/calls/initiate/: avvia chiamata
    - Genera call_id (UUID)
    - Invia notifica a target_user_id: "Chiamata in arrivo da [Nome]"
    - Risponde: { "call_id": "...", "ws_url": "ws://host/ws/call/{call_id}/" }
  
  POST /api/chat/calls/{call_id}/end/: termina chiamata
    - Invia messaggio WebSocket call_ended a tutti i partecipanti
    - Registra AuditLog: call terminata, durata

Configura STUN server in settings:
  WEBRTC_ICE_SERVERS = [
    {"urls": "stun:stun.l.google.com:19302"},
    {"urls": "stun:stun1.l.google.com:19302"},
  ]
  Esponi come: GET /api/chat/ice_servers/ → lista STUN servers

TEST `backend/apps/chat/tests/test_calls.py`:
  - Initiate call: call_id generato, notifica inviata
  - End call: AuditLog creato
  (I test WebRTC completi richiedono browser reale — testati via E2E)

Esegui: `pytest backend/apps/chat/tests/test_calls.py -v`
```

---

## STEP 9C.4 — Frontend: Chat UI e Videochiamata

### Prompt per Cursor:

```
Crea l'interfaccia chat e videochiamata nel frontend.

Installa dipendenze npm:
  npm install simple-peer uuid
  (simple-peer: wrapper WebRTC, uuid: generazione call_id)

Aggiungi `frontend/src/services/chatService.ts`:
  - getChatRooms(): GET /api/chat/rooms/
  - createDirectChat(userId): POST /api/chat/rooms/direct/
  - getRoomMessages(roomId, page): GET /api/chat/rooms/{id}/messages/
  - sendMessage(roomId, content, replyTo?): POST REST fallback
  - uploadChatFile(roomId, file): POST /api/chat/rooms/{id}/upload/
  - deleteMessage(messageId): DELETE
  - getUnreadCount(): GET /api/chat/unread_count/
  - initiateCall(targetUserId): POST /api/chat/calls/initiate/
  - endCall(callId): POST /api/chat/calls/{id}/end/
  - getIceServers(): GET /api/chat/ice_servers/

Aggiungi `frontend/src/hooks/useWebSocket.ts`:
  Hook personalizzato per connessione WebSocket:
  - Connessione automatica con JWT nel query param
  - Riconnessione automatica con backoff esponenziale
  - Cleanup alla disconnessione del componente

Aggiungi `frontend/src/hooks/useChatRoom.ts`:
  Hook per gestione singola chat room:
  - messages: ChatMessage[]
  - sendMessage(content, replyTo?)
  - uploadFile(file)
  - typingUsers: string[] (utenti che stanno digitando)
  - onlineMembers: string[] (user IDs online)
  - isConnected: bool

Crea `frontend/src/components/chat/`:

ChatPanel.tsx (pannello laterale, drawer):
  - Apre da icona chat nella navbar
  - Header: "Chat" + badge unread totale
  - Lista room: nome, avatar, ultimo messaggio, unread badge, timestamp
  - Ricerca room per nome utente
  - Click su room → apre ChatWindow
  - Bottone "Nuova chat" → select utente

ChatWindow.tsx:
  - Header: nome utente/gruppo, presenza (• Online / Ultima vista X)
    Bottone "Chiama" (avvia videochiamata) + bottone chiudi
  - Area messaggi: lista con data separator ("Oggi", "Ieri", date)
  - Messaggi:
    * Propri: allineati a destra, sfondo blu
    * Altrui: allineati a sinistra, sfondo grigio, nome mittente
    * File: card con icona file, nome, dimensione, download
    * Immagine: preview inline
    * Risposta: card indent con messaggio originale
    * Sistema: centrato, grigio, corsivo
  - Indicatore "sta digitando..." (scompare dopo 3s di inattività)
  - Input area:
    * Textarea multi-riga (Enter invia, Shift+Enter va a capo)
    * Bottone allegato (upload file)
    * Bottone emoji (picker base)
    * Preview reply: X per annullare
    * Invio

ChatMessage.tsx:
  - Singolo messaggio con tutti gli stati
  - Context menu on hover/long press: Rispondi, Elimina (solo propri)
  - Timestamp relativo (es. "14:32") con tooltip data completa

DocumentChatButton.tsx:
  - Piccolo bottone "Chat" nel DocumentDetailPanel header
  - Badge con unread count della chat del documento
  - Click → apre ChatWindow per la chat del documento

VideoCallModal.tsx:
  UI videochiamata a schermo intero o grande modale:
  
  Stati:
  1. Chiamata in uscita:
     - Avatar + nome del destinatario
     - "Chiamata in corso..." + animazione
     - Bottone "Annulla"
  
  2. Chiamata in arrivo (notifica push):
     - Modale piccolo: "Chiamata da [Nome]"
     - Bottone "Accetta" (verde) + "Rifiuta" (rosso)
  
  3. Chiamata attiva:
     - Video remoto: grande, a schermo intero
     - Video locale: piccolo, angolo in basso a destra (picture-in-picture)
     - Se audio/video disabilitato: placeholder con iniziali
     - Barra controlli in basso (scompare dopo 3s, riappare on hover):
       * Mute microfono (toggle)
       * Disabilita/abilita camera
       * Condividi schermo (Screen Sharing API)
       * Termina chiamata (rosso)
     - Timer chiamata (00:00:00)
  
  4. Chiamata terminata:
     - "Chiamata terminata" + durata
     - Auto-chiude dopo 3s

useWebRTC.ts (hook):
  Gestisce tutto il ciclo WebRTC:
  - initCall(callId, targetUserId, isInitiator): configura peer
  - localStream: MediaStream (camera + mic)
  - remoteStream: MediaStream (stream remoto)
  - isMuted, isCameraOff, isScreenSharing: stati
  - toggleMute(), toggleCamera(), shareScreen(), endCall()
  - Usa simple-peer per astrazione WebRTC
  - Scambia offer/answer/ICE via WebSocket CallConsumer

Aggiorna navbar Layout.tsx:
  - Aggiungi icona chat con badge unread count
  - Click → apre/chiude ChatPanel
  - IncomingCallNotification: ascolta notifiche chiamata in arrivo

Crea `frontend/src/pages/ChatPage.tsx` (route: /chat, opzionale):
  Versione a pagina intera della chat (per schermi piccoli)

TEST Vitest:
  - ChatWindow: render messaggi, invio, indicatore digitazione
  - ChatPanel: lista room, unread badge
  - VideoCallModal: stati chiamata in uscita/in arrivo/attiva
  - useWebRTC: mock MediaDevices, peer connection setup

TEST E2E (aggiunta a Fase 8):
  Aggiungi spec `frontend/e2e/chat.spec.ts`:
  - Login utente A e B in due tab
  - A invia messaggio a B → B vede messaggio in real-time
  - B risponde → A vede risposta
  - Unread count si azzera dopo apertura chat

Esegui: `npm run test -- --run`
Esegui: `npm run build`
```

---

## TEST INTEGRAZIONE FASE 9C

### Prompt per Cursor:

```
Test di integrazione Fase 9C.

1. `pytest backend/apps/chat/ -v --cov=apps/chat`

2. `npm run test -- --run`

3. Test manuale chat:
   a) Login come admin in tab 1, login come operatore in tab 2
   b) Admin: apri ChatPanel → "Nuova chat" → seleziona operatore
      → ChatWindow aperta
   c) Admin invia messaggio "Ciao!" → apparisce nella chat
   d) Operatore (tab 2): notifica badge in navbar, apri chat
      → messaggio "Ciao!" visibile
   e) Operatore risponde → admin vede in tempo reale
   f) Admin vede "sta digitando..." mentre operatore scrive
   g) Upload file in chat → operatore scarica il file
   h) Apri DocumentDetailPanel → bottone Chat → 
      ChatWindow per il documento specifico
   
4. Test videochiamata:
   a) Admin clicca "Chiama" nell'header della chat con operatore
   b) Operatore vede notifica "Chiamata da Admin"
   c) Operatore accetta → VideoCallModal si apre su entrambi
   d) Verifica: video locale visibile (richiede webcam), stream remoto
   e) Mute/unmute microfono → indicatore aggiornato
   f) Termina chiamata → modal si chiude

5. Redis:
   Verifica che Redis sia attivo: `docker-compose exec redis redis-cli ping`
   → risposta: PONG

Crea `FASE_09C_TEST_REPORT.md`.
```
