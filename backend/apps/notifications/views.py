"""
API Notifiche (FASE 12).
"""
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.organizations.mixins import TenantFilterMixin
from drf_spectacular.utils import extend_schema, extend_schema_view
from .models import Notification
from .serializers import NotificationSerializer, MarkReadSerializer


@extend_schema_view(
    list=extend_schema(tags=["Notifiche"], summary="Lista notifiche"),
    retrieve=extend_schema(tags=["Notifiche"], summary="Dettaglio notifica"),
)
class NotificationViewSet(TenantFilterMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    queryset = Notification.objects.all()

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(recipient=self.request.user)
            .order_by("-created_at")
        )

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        unread = request.query_params.get("unread")
        read_param = request.query_params.get("read")
        if unread == "true":
            qs = qs.filter(is_read=False)
        if read_param == "true":
            qs = qs.filter(is_read=True)
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(NotificationSerializer(page, many=True).data)
        return Response(NotificationSerializer(qs, many=True).data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if not instance.is_read:
            instance.is_read = True
            instance.read_at = timezone.now()
            instance.save(update_fields=["is_read", "read_at"])
        return Response(NotificationSerializer(instance).data)

    @action(detail=False, methods=["post"], url_path="mark_read")
    def mark_read(self, request):
        ser = MarkReadSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        qs = Notification.objects.filter(recipient=request.user)
        if ser.validated_data.get("all"):
            updated = qs.filter(is_read=False).update(is_read=True, read_at=timezone.now())
            return Response({"marked": updated})
        ids = ser.validated_data.get("ids") or []
        if not ids:
            return Response({"marked": 0})
        updated = qs.filter(id__in=ids, is_read=False).update(is_read=True, read_at=timezone.now())
        return Response({"marked": updated})

    @action(detail=False, methods=["get"], url_path="unread_count")
    def unread_count(self, request):
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return Response({"count": count})

    @action(detail=False, methods=["get"], url_path="poll")
    def poll(self, request):
        """Polling per aggiornare unread_count (es. ogni 30s)."""
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return Response({"unread_count": count})
