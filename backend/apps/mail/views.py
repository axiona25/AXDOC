"""
API client di posta PEC/Email.
"""
import imaplib
import smtplib

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.users.permissions import IsAdminRole

from .imap_client import fetch_new_emails
from .models import MailAccount, MailMessage
from .serializers import (
    MailAccountCreateSerializer,
    MailAccountSerializer,
    MailMessageDetailSerializer,
    MailMessageListSerializer,
    SendMailSerializer,
)
from .smtp_client import send_email


class MailAccountViewSet(viewsets.ModelViewSet):
    """CRUD account di posta. Solo ADMIN."""

    queryset = MailAccount.objects.all()
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return MailAccountCreateSerializer
        return MailAccountSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"], url_path="test_connection")
    def test_connection(self, request, pk=None):
        """Testa connessione IMAP e SMTP."""
        account = self.get_object()
        results = {"imap": False, "smtp": False, "imap_error": "", "smtp_error": ""}

        try:
            if account.imap_use_ssl:
                conn = imaplib.IMAP4_SSL(account.imap_host, account.imap_port)
            else:
                conn = imaplib.IMAP4(account.imap_host, account.imap_port)
            conn.login(account.imap_username, account.imap_password)
            conn.logout()
            results["imap"] = True
        except Exception as e:
            results["imap_error"] = str(e)

        try:
            if account.smtp_use_ssl:
                server = smtplib.SMTP_SSL(account.smtp_host, account.smtp_port)
            else:
                server = smtplib.SMTP(account.smtp_host, account.smtp_port)
                if account.smtp_use_tls:
                    server.starttls()
            server.login(account.smtp_username, account.smtp_password)
            server.quit()
            results["smtp"] = True
        except Exception as e:
            results["smtp_error"] = str(e)

        return Response(results)

    @action(detail=True, methods=["post"], url_path="fetch_now")
    def fetch_now(self, request, pk=None):
        """Trigger manuale fetch IMAP."""
        account = self.get_object()
        count = fetch_new_emails(account)
        return Response({"fetched": count})


class MailMessageViewSet(viewsets.ModelViewSet):
    """Lista, dettaglio, invio email. Utenti autenticati."""

    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch", "delete"]

    def create(self, request, *args, **kwargs):
        return Response(
            {"detail": "Usa POST /api/mail/messages/send/ per inviare un messaggio."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def get_queryset(self):
        qs = MailMessage.objects.all().select_related("account")
        account_id = self.request.query_params.get("account")
        if account_id:
            qs = qs.filter(account_id=account_id)
        folder = self.request.query_params.get("folder")
        if folder:
            qs = qs.filter(folder=folder)
        direction = self.request.query_params.get("direction")
        if direction in ("in", "out"):
            qs = qs.filter(direction=direction)
        mail_status = self.request.query_params.get("status")
        if mail_status:
            qs = qs.filter(status=mail_status)
        search = (self.request.query_params.get("search") or "").strip()
        if search:
            from django.db.models import Q

            qs = qs.filter(
                Q(subject__icontains=search)
                | Q(from_address__icontains=search)
                | Q(from_name__icontains=search)
            )
        protocol_id = self.request.query_params.get("protocol")
        if protocol_id:
            qs = qs.filter(protocol_id=protocol_id)
        return qs.order_by("-sent_at")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return MailMessageDetailSerializer
        return MailMessageListSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status == "unread":
            instance.status = "read"
            instance.save(update_fields=["status"])
        return Response(
            MailMessageDetailSerializer(instance, context={"request": request}).data
        )

    @action(detail=False, methods=["post"], url_path="send")
    def send_message(self, request):
        """Invia una nuova email."""
        serializer = SendMailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            account = MailAccount.objects.get(pk=data["account_id"], is_active=True)
        except MailAccount.DoesNotExist:
            return Response(
                {"account_id": "Account non trovato o non attivo."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reply_to = None
        if data.get("reply_to_message_id"):
            reply_to = MailMessage.objects.filter(pk=data["reply_to_message_id"]).first()

        attachments = []
        for _key, uploaded_file in request.FILES.items():
            attachments.append(
                {
                    "filename": uploaded_file.name,
                    "content_type": uploaded_file.content_type or "application/octet-stream",
                    "data": uploaded_file.read(),
                }
            )

        try:
            mail_msg = send_email(
                account=account,
                to_addresses=data["to"],
                subject=data["subject"],
                body_text=data.get("body_text", ""),
                body_html=data.get("body_html", ""),
                cc_addresses=data.get("cc"),
                bcc_addresses=data.get("bcc"),
                attachments=attachments if attachments else None,
                reply_to_message=reply_to,
            )
            if data.get("protocol_id"):
                mail_msg.protocol_id = data["protocol_id"]
                mail_msg.save(update_fields=["protocol"])

            return Response(
                MailMessageDetailSerializer(mail_msg, context={"request": request}).data,
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return Response({"detail": f"Errore invio: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=["post"], url_path="mark_read")
    def mark_read(self, request, pk=None):
        msg = self.get_object()
        msg.status = "read"
        msg.save(update_fields=["status"])
        return Response({"status": "read"})

    @action(detail=True, methods=["post"], url_path="mark_unread")
    def mark_unread(self, request, pk=None):
        msg = self.get_object()
        msg.status = "unread"
        msg.save(update_fields=["status"])
        return Response({"status": "unread"})

    @action(detail=True, methods=["post"], url_path="toggle_star")
    def toggle_star(self, request, pk=None):
        msg = self.get_object()
        msg.is_starred = not msg.is_starred
        msg.save(update_fields=["is_starred"])
        return Response({"is_starred": msg.is_starred})

    @action(detail=True, methods=["post"], url_path="link_protocol")
    def link_protocol(self, request, pk=None):
        """Associa email a un protocollo."""
        from apps.protocols.models import Protocol

        msg = self.get_object()
        protocol_id = request.data.get("protocol_id")
        if not protocol_id:
            return Response({"protocol_id": "Obbligatorio."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            protocol = Protocol.objects.get(pk=protocol_id)
            msg.protocol = protocol
            msg.save(update_fields=["protocol"])
            return Response({"linked": True, "protocol_id": str(protocol.id)})
        except Protocol.DoesNotExist:
            return Response({"protocol_id": "Protocollo non trovato."}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="unlink_protocol")
    def unlink_protocol(self, request, pk=None):
        """Rimuove associazione email-protocollo."""
        msg = self.get_object()
        msg.protocol = None
        msg.save(update_fields=["protocol"])
        return Response({"linked": False})
