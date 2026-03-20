"""
API Workflow: template, step, istanze (RF-048..RF-057).
"""
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.users.guest_permissions import IsInternalUser
from .models import WorkflowTemplate, WorkflowStep, WorkflowInstance, WorkflowStepInstance
from .serializers import (
    WorkflowTemplateListSerializer,
    WorkflowTemplateDetailSerializer,
    WorkflowStepSerializer,
    WorkflowInstanceSerializer,
)
from .services import WorkflowService
from apps.users.permissions import IsAdminRole


class WorkflowTemplateViewSet(viewsets.ModelViewSet):
    """CRUD template workflow. Create/update/destroy solo ADMIN (RF-048, RF-050). Solo utenti interni (FASE 17)."""
    queryset = WorkflowTemplate.objects.filter(is_deleted=False)
    permission_classes = [IsAuthenticated, IsInternalUser]

    def get_queryset(self):
        qs = WorkflowTemplate.objects.filter(is_deleted=False)
        if self.request.query_params.get("mine") == "true" and self.request.user:
            qs = qs.filter(created_by=self.request.user)
        return qs.order_by("name")

    def get_serializer_class(self):
        if self.action in ("list",):
            return WorkflowTemplateListSerializer
        return WorkflowTemplateDetailSerializer

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy", "publish", "unpublish"):
            return [IsAuthenticated(), IsAdminRole()]
        return [IsAuthenticated()]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.instances.filter(status="active").exists():
            return Response(
                {"detail": "Impossibile eliminare: esistono istanze attive."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        instance.is_deleted = True
        instance.save(update_fields=["is_deleted"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_published:
            return Response(
                {"detail": "Workflow pubblicato non modificabile."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if instance.instances.filter(status="active").exists():
            return Response(
                {"detail": "Esistono istanze attive. Annullarle prima di modificare."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().update(request, *args, **kwargs)

    @action(detail=True, methods=["post"], url_path="publish")
    def publish(self, request, pk=None):
        """Pubblica il workflow (is_published=True)."""
        template = self.get_object()
        if template.is_published:
            return Response({"detail": "Già pubblicato."}, status=status.HTTP_400_BAD_REQUEST)
        template.is_published = True
        template.save(update_fields=["is_published"])
        return Response(WorkflowTemplateDetailSerializer(template).data)

    @action(detail=True, methods=["post"], url_path="unpublish")
    def unpublish(self, request, pk=None):
        """Rimuovi pubblicazione (solo se nessuna istanza attiva)."""
        template = self.get_object()
        if template.instances.filter(status="active").exists():
            return Response(
                {"detail": "Esistono istanze attive. Impossibile rimuovere pubblicazione."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        template.is_published = False
        template.save(update_fields=["is_published"])
        return Response(WorkflowTemplateDetailSerializer(template).data)

    @action(detail=True, methods=["get"], url_path="steps")
    def steps_list(self, request, pk=None):
        """Lista step del template."""
        template = self.get_object()
        steps = template.steps.all().order_by("order")
        return Response(WorkflowStepSerializer(steps, many=True).data)


class WorkflowStepViewSet(viewsets.ModelViewSet):
    """CRUD step (nested sotto template). Solo ADMIN."""
    serializer_class = WorkflowStepSerializer
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get_queryset(self):
        template_id = self.kwargs.get("template_pk")
        return WorkflowStep.objects.filter(template_id=template_id).order_by("order")

    def perform_create(self, serializer):
        template_id = self.kwargs["template_pk"]
        template = WorkflowTemplate.objects.get(pk=template_id)
        if template.is_published:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Non modificare un template pubblicato.")
        max_order = template.steps.aggregate(m=Max("order"))["m"] or 0
        serializer.save(template=template, order=max_order + 1)

    def perform_update(self, serializer):
        if serializer.instance.template.is_published:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Non modificare un template pubblicato.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.template.is_published:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Non modificare un template pubblicato.")
        instance.delete()


from django.db.models import Max


class WorkflowInstanceViewSet(viewsets.ReadOnlyModelViewSet):
    """Lista e dettaglio istanze workflow. Filtro per utente assegnato (RF-056). Solo utenti interni (FASE 17)."""
    serializer_class = WorkflowInstanceSerializer
    permission_classes = [IsAuthenticated, IsInternalUser]

    def get_queryset(self):
        user = self.request.user
        qs = WorkflowInstance.objects.all().select_related("template", "document", "started_by").prefetch_related("step_instances", "step_instances__step")
        if getattr(user, "role", None) != "ADMIN":
            qs = qs.filter(
                step_instances__assigned_to=user,
                status="active",
            ).distinct()
        document_id = self.request.query_params.get("document_id")
        if document_id:
            qs = qs.filter(document_id=document_id)
        template_id = self.request.query_params.get("template_id")
        if template_id:
            qs = qs.filter(template_id=template_id)
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs.order_by("-started_at")
