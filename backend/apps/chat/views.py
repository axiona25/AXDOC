"""
REST API Chat (FASE 13).
"""
import uuid
from django.utils import timezone
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.views import APIView

from .models import ChatRoom, ChatMessage, ChatMembership
from apps.organizations.mixins import TenantFilterMixin
from drf_spectacular.utils import extend_schema, extend_schema_view
from .serializers import ChatRoomSerializer, ChatMessageSerializer, ChatMembershipSerializer


@extend_schema_view(
    list=extend_schema(tags=["Chat"], summary="Lista stanze chat"),
    create=extend_schema(tags=["Chat"], summary="Crea stanza chat"),
    retrieve=extend_schema(tags=["Chat"], summary="Dettaglio stanza"),
)
class ChatRoomViewSet(TenantFilterMixin, viewsets.ModelViewSet):
    serializer_class = ChatRoomSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    queryset = ChatRoom.objects.all()

    def get_queryset(self):
        return super().get_queryset().filter(
            is_active=True,
            memberships__user=self.request.user,
        ).distinct().prefetch_related("memberships__user", "messages").order_by("-created_at")

    def update(self, request, *args, **kwargs):
        return Response({"detail": "Non supportato."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def partial_update(self, request, *args, **kwargs):
        return Response({"detail": "Non supportato."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def destroy(self, request, *args, **kwargs):
        return Response({"detail": "Non supportato."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(detail=False, methods=["post"], url_path="direct")
    def create_direct(self, request):
        user_id = request.data.get("user_id")
        if not user_id:
            return Response({"user_id": "Obbligatorio."}, status=status.HTTP_400_BAD_REQUEST)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        other = User.objects.filter(pk=user_id).first()
        if not other:
            return Response({"user_id": "Utente non trovato."}, status=status.HTTP_400_BAD_REQUEST)
        if other.id == request.user.id:
            return Response({"user_id": "Non puoi creare una chat con te stesso."}, status=status.HTTP_400_BAD_REQUEST)
        room = ChatRoom.get_or_create_direct(request.user, other)
        return Response(ChatRoomSerializer(room, context={"request": request}).data)

    def create(self, request, *args, **kwargs):
        name = (request.data.get("name") or "").strip()
        member_ids = request.data.get("member_ids") or []
        if not name:
            return Response({"name": "Obbligatorio."}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(member_ids, list):
            return Response({"member_ids": "Lista di UUID."}, status=status.HTTP_400_BAD_REQUEST)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        users = list(User.objects.filter(pk__in=member_ids))
        if request.user.id not in [u.id for u in users]:
            users.append(request.user)
        t = getattr(request, "tenant", None)
        room = ChatRoom.objects.create(
            room_type="group", name=name, created_by=request.user, tenant=t
        )
        for u in users:
            ChatMembership.objects.get_or_create(room=room, user=u, defaults={"is_admin": u.id == request.user.id})
        return Response(ChatRoomSerializer(room, context={"request": request}).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get", "post"], url_path="messages")
    def messages_list(self, request, pk=None):
        room = self.get_object()
        if request.method == "POST":
            return self._send_message(request, room)
        page = int(request.query_params.get("page", 1))
        page_size = min(50, max(1, int(request.query_params.get("page_size", 50))))
        qs = room.messages.filter(is_deleted=False).select_related("sender").order_by("-sent_at")
        start = (page - 1) * page_size
        msgs = list(qs[start : start + page_size])
        msgs.reverse()
        return Response({
            "results": ChatMessageSerializer(msgs, many=True).data,
            "count": qs.count(),
        })

    def _send_message(self, request, room):
        content = (request.data.get("content") or "").strip()
        reply_to = request.data.get("reply_to")
        if not content and not request.FILES.get("file") and not request.FILES.get("image"):
            return Response({"content": "Testo o file obbligatorio."}, status=status.HTTP_400_BAD_REQUEST)
        reply_to = request.data.get("reply_to")
        msg_type = "text"
        file_obj = request.FILES.get("file") or request.FILES.get("image")
        if file_obj:
            msg_type = "image" if (file_obj.content_type or "").startswith("image/") else "file"
        msg = ChatMessage.objects.create(
            room=room,
            sender=request.user,
            message_type=msg_type,
            content=content,
            reply_to_id=reply_to,
        )
        if file_obj:
            if msg_type == "image":
                msg.image.save(file_obj.name or "image", file_obj, save=True)
            else:
                msg.file.save(file_obj.name or "file", file_obj, save=True)
            msg.file_name = file_obj.name or ""
            msg.file_size = file_obj.size
            msg.save(update_fields=["file_name", "file_size"])
        return Response(ChatMessageSerializer(msg).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="upload")
    def upload(self, request, pk=None):
        room = self.get_object()
        file_obj = request.FILES.get("file") or request.FILES.get("file_upload")
        if not file_obj:
            return Response({"file": "Obbligatorio."}, status=status.HTTP_400_BAD_REQUEST)
        msg_type = "image" if (file_obj.content_type or "").startswith("image/") else "file"
        msg = ChatMessage.objects.create(
            room=room,
            sender=request.user,
            message_type=msg_type,
            content=file_obj.name or "",
        )
        if msg_type == "image":
            msg.image.save(file_obj.name or "image", file_obj, save=True)
        else:
            msg.file.save(file_obj.name or "file", file_obj, save=True)
        msg.file_name = file_obj.name or ""
        msg.file_size = file_obj.size
        msg.save(update_fields=["file_name", "file_size"])
        return Response(ChatMessageSerializer(msg).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="mark_read")
    def mark_read(self, request, pk=None):
        room = self.get_object()
        now = timezone.now()
        ChatMembership.objects.filter(room=room, user=request.user).update(last_read_at=now)
        return Response({"ok": True})

    @action(detail=True, methods=["get"], url_path="members")
    def members_list(self, request, pk=None):
        room = self.get_object()
        return Response(ChatMembershipSerializer(room.memberships.all(), many=True).data)

    @action(detail=False, methods=["get"], url_path="unread_count")
    def unread_count(self, request):
        total = 0
        for room in self.get_queryset():
            mem = room.memberships.filter(user=request.user).first()
            if not mem or not mem.last_read_at:
                total += room.messages.filter(is_deleted=False).count()
            else:
                total += room.messages.filter(is_deleted=False, sent_at__gt=mem.last_read_at).count()
        return Response({"count": total})


class ChatMessageViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]

    def destroy(self, request, pk=None):
        msg = ChatMessage.objects.filter(pk=pk, sender=request.user).first()
        if not msg:
            return Response({"detail": "Non trovato o non autorizzato."}, status=status.HTTP_404_NOT_FOUND)
        msg.is_deleted = True
        msg.save(update_fields=["is_deleted"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class CallInitiateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        target_user_id = request.data.get("target_user_id")
        if not target_user_id:
            return Response({"target_user_id": "Obbligatorio."}, status=status.HTTP_400_BAD_REQUEST)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        target = User.objects.filter(pk=target_user_id).first()
        if not target:
            return Response({"target_user_id": "Utente non trovato."}, status=status.HTTP_400_BAD_REQUEST)
        call_id = uuid.uuid4()
        try:
            from apps.notifications.services import NotificationService
            name = getattr(request.user, "email", str(request.user))
            if getattr(request.user, "first_name", None) or getattr(request.user, "last_name", None):
                name = f"{getattr(request.user, 'first_name', '')} {getattr(request.user, 'last_name', '')}".strip()
            NotificationService.send(
                target,
                "system",
                "Chiamata in arrivo",
                f"{name} ti sta chiamando.",
                link_url=f"/call/{call_id}",
                metadata={"call_id": str(call_id), "from_user_id": str(request.user.id)},
            )
        except Exception:
            pass
        base_url = getattr(settings, "WEBSOCKET_URL", request.build_absolute_uri("/").rstrip("/").replace("http", "ws"))
        ws_url = f"{base_url}/ws/call/{call_id}/"
        return Response({"call_id": str(call_id), "ws_url": ws_url})


class CallEndView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, call_id):
        try:
            from apps.authentication.models import AuditLog
            AuditLog.log(
                request.user,
                "CALL_ENDED",
                {"call_id": str(call_id), "detail": "videochiamata terminata"},
                request,
            )
        except Exception:
            pass
        return Response({"ok": True})


class IceServersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        servers = getattr(settings, "WEBRTC_ICE_SERVERS", [
            {"urls": "stun:stun.l.google.com:19302"},
        ])
        return Response({"ice_servers": servers})
