"""
API Workflow: template, step, istanze (RF-048..RF-057).
"""
from datetime import timedelta

from django.db.models import Max, Q
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
from .notifications import (
    notify_step_assigned,
    notify_step_completed,
    notify_step_rejected,
    notify_workflow_cancelled,
    notify_workflow_completed,
)
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

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

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


class WorkflowInstanceViewSet(viewsets.ModelViewSet):
    """
    Istanze workflow: lista, dettaglio, avvio, azione step (RF-053..RF-056).
    Solo utenti interni.
    """
    serializer_class = WorkflowInstanceSerializer
    permission_classes = [IsAuthenticated, IsInternalUser]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        qs = WorkflowInstance.objects.all().select_related(
            "template", "document", "started_by"
        ).prefetch_related(
            "step_instances", "step_instances__step", "step_instances__assigned_to"
        )
        if getattr(user, "role", None) != "ADMIN":
            qs = qs.filter(
                Q(started_by=user) |
                Q(step_instances__assigned_to=user)
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

    def create(self, request, *args, **kwargs):
        """
        POST /api/workflows/instances/
        Body: { "template": "<template_id>", "document": "<document_id>" }
        Avvia un workflow su un documento.
        """
        template_id = request.data.get("template")
        document_id = request.data.get("document")

        if not template_id or not document_id:
            return Response(
                {"detail": "Campi 'template' e 'document' obbligatori."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            template = WorkflowTemplate.objects.get(pk=template_id, is_published=True, is_deleted=False)
        except WorkflowTemplate.DoesNotExist:
            return Response(
                {"detail": "Template non trovato o non pubblicato."},
                status=status.HTTP_404_NOT_FOUND,
            )

        from apps.documents.models import Document

        try:
            document = Document.objects.get(pk=document_id, is_deleted=False)
        except Document.DoesNotExist:
            return Response(
                {"detail": "Documento non trovato."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Verifica che non esista già un workflow attivo sullo stesso documento
        if WorkflowInstance.objects.filter(document=document, status="active").exists():
            return Response(
                {"detail": "Esiste già un workflow attivo su questo documento."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verifica che il template abbia almeno uno step
        steps = template.steps.all().order_by("order")
        if not steps.exists():
            return Response(
                {"detail": "Il template non ha step definiti."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Crea l'istanza
        instance = WorkflowInstance.objects.create(
            template=template,
            document=document,
            started_by=request.user,
            current_step_order=steps.first().order,
        )

        # Crea le step instances e assegna gli utenti
        for step in steps:
            si = WorkflowStepInstance.objects.create(
                workflow_instance=instance,
                step=step,
                status="pending",
            )
            # Calcola deadline
            if step.deadline_days:
                si.deadline = timezone.now() + timedelta(days=step.deadline_days)
                si.save(update_fields=["deadline"])
            # Assegna utenti
            assignees = WorkflowService.get_assignees(step, document)
            if assignees:
                si.assigned_to.set(assignees)

        # Assicura accesso in lettura al documento per tutti gli assegnatari
        from apps.documents.models import DocumentPermission

        all_assignee_ids = set()
        for si in instance.step_instances.all():
            all_assignee_ids.update(si.assigned_to.values_list("pk", flat=True))
        for user_id in all_assignee_ids:
            DocumentPermission.objects.get_or_create(
                document=document,
                user_id=user_id,
                defaults={"can_read": True, "can_write": False, "can_delete": False},
            )

        # Attiva il primo step
        first_si = instance.step_instances.filter(step__order=instance.current_step_order).first()
        if first_si:
            first_si.status = "in_progress"
            first_si.started_at = timezone.now()
            first_si.save(update_fields=["status", "started_at"])
            notify_step_assigned(first_si)

        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="action")
    def step_action(self, request, pk=None):
        """
        POST /api/workflows/instances/{id}/action/
        Body: { "action": "approve|reject|complete", "comment": "..." }
        Completa o rifiuta lo step corrente.
        """
        instance = self.get_object()

        if instance.status != "active":
            return Response(
                {"detail": "Workflow non attivo."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        action_taken = request.data.get("action")
        comment = request.data.get("comment", "")

        if action_taken not in ("approve", "reject", "complete"):
            return Response(
                {"detail": "Azione non valida. Usa: approve, reject, complete."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Trova lo step corrente
        current_si = instance.step_instances.filter(
            step__order=instance.current_step_order,
            status="in_progress",
        ).first()

        if not current_si:
            return Response(
                {"detail": "Nessuno step in corso."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verifica che l'utente sia assegnato allo step (o sia ADMIN)
        is_assigned = current_si.assigned_to.filter(pk=request.user.pk).exists()
        is_admin = getattr(request.user, "role", None) == "ADMIN"
        if not is_assigned and not is_admin:
            return Response(
                {"detail": "Non sei assegnato a questo step."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Completa lo step
        current_si.status = "completed" if action_taken in ("approve", "complete") else "rejected"
        current_si.completed_at = timezone.now()
        current_si.completed_by = request.user
        current_si.action_taken = action_taken
        current_si.comment = comment
        current_si.save(update_fields=["status", "completed_at", "completed_by", "action_taken", "comment"])

        if action_taken == "reject":
            # Rifiuto → workflow rifiutato
            instance.status = "rejected"
            instance.completed_at = timezone.now()
            instance.save(update_fields=["status", "completed_at"])
            notify_step_rejected(current_si, request.user)
        else:
            # Trova il prossimo step
            next_steps = instance.step_instances.filter(
                step__order__gt=instance.current_step_order,
            ).order_by("step__order")

            # Salta step non obbligatori senza assegnatari
            next_si = None
            for candidate in next_steps:
                if not candidate.step.is_required and candidate.assigned_to.count() == 0:
                    candidate.status = "skipped"
                    candidate.save(update_fields=["status"])
                    continue
                next_si = candidate
                break

            if next_si:
                # Avanza al prossimo step
                instance.current_step_order = next_si.step.order
                instance.save(update_fields=["current_step_order"])
                next_si.status = "in_progress"
                next_si.started_at = timezone.now()
                next_si.save(update_fields=["status", "started_at"])
                # Accesso lettura per nuovi assegnatari
                from apps.documents.models import DocumentPermission

                for uid in next_si.assigned_to.values_list("pk", flat=True):
                    DocumentPermission.objects.get_or_create(
                        document=instance.document,
                        user_id=uid,
                        defaults={"can_read": True, "can_write": False, "can_delete": False},
                    )
                notify_step_completed(current_si, request.user)
                notify_step_assigned(next_si)
            else:
                # Tutti gli step completati → workflow completato
                instance.status = "completed"
                instance.completed_at = timezone.now()
                instance.save(update_fields=["status", "completed_at"])
                notify_step_completed(current_si, request.user)
                notify_workflow_completed(instance)

        # Ricarica e ritorna
        instance.refresh_from_db()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel_workflow(self, request, pk=None):
        """
        POST /api/workflows/instances/{id}/cancel/
        Annulla un workflow attivo. Solo chi l'ha avviato o ADMIN.
        """
        instance = self.get_object()

        if instance.status != "active":
            return Response(
                {"detail": "Workflow non attivo."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        is_starter = instance.started_by == request.user
        is_admin = getattr(request.user, "role", None) == "ADMIN"
        if not is_starter and not is_admin:
            return Response(
                {"detail": "Solo chi ha avviato il workflow o un admin può annullarlo."},
                status=status.HTTP_403_FORBIDDEN,
            )

        instance.status = "cancelled"
        instance.completed_at = timezone.now()
        instance.save(update_fields=["status", "completed_at"])
        notify_workflow_cancelled(instance, request.user)

        serializer = self.get_serializer(instance)
        return Response(serializer.data)
