"""
Servizi workflow: calcolo assegnatari, scadenze (RF-051, RF-057).
"""
import logging

from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)


class WorkflowService:
    """Logica assegnatari e reminder per step workflow."""

    @staticmethod
    def get_assignees(step, document):
        """
        Ritorna lista di User assegnati allo step per il dato documento.
        - role: tutti gli utenti con quel ruolo globale
        - specific_user: l'utente specificato
        - ou_role: utenti con assignee_ou_role nell'UO assignee_ou
        - document_ou: utenti nelle UO che hanno accesso al documento (ou_permissions)
        """
        if step.assignee_type == "role" and step.assignee_role:
            return list(User.objects.filter(role=step.assignee_role, is_active=True))
        if step.assignee_type == "specific_user" and step.assignee_user_id:
            return [step.assignee_user] if step.assignee_user else []
        if step.assignee_type == "ou_role":
            from apps.organizations.models import OrganizationalUnitMembership

            ou = step.assignee_ou
            role = step.assignee_ou_role or step.assignee_role
            if not ou:
                return []
            qs = OrganizationalUnitMembership.objects.filter(
                organizational_unit=ou,
                is_active=True,
            )
            if role:
                qs = qs.filter(role__iexact=role.strip())
            user_ids = qs.values_list("user_id", flat=True).distinct()
            result = list(User.objects.filter(pk__in=user_ids, is_active=True))
            if not result:
                logger.warning(
                    "Workflow ou_role: nessun membro attivo con ruolo %r nell'UO %s per lo step %r.",
                    role,
                    ou,
                    getattr(step, "name", None) or step.pk,
                )
                u = getattr(step, "assignee_user", None)
                if step.assignee_user_id and u is not None and getattr(u, "is_active", True):
                    logger.warning(
                        "Workflow ou_role: uso assignee_user come fallback per lo step %r.",
                        getattr(step, "name", None) or step.pk,
                    )
                    result = [u]
            return result
        if step.assignee_type == "document_ou":
            ou_ids = document.ou_permissions.values_list("organizational_unit_id", flat=True).distinct()
            if not ou_ids:
                return []
            from apps.organizations.models import OrganizationalUnitMembership

            user_ids = OrganizationalUnitMembership.objects.filter(
                organizational_unit_id__in=ou_ids,
                is_active=True,
            ).values_list("user_id", flat=True).distinct()
            return list(User.objects.filter(pk__in=user_ids, is_active=True))
        return []

    @staticmethod
    def check_deadline_violations():
        """
        Trova step istanza scaduti e invia reminder.
        Da chiamare con cron/celery; per ora solo metodo stub.
        """
        from django.utils import timezone
        from .models import WorkflowStepInstance

        now = timezone.now()
        overdue = WorkflowStepInstance.objects.filter(
            status="in_progress",
            deadline__isnull=False,
            deadline__lt=now,
            workflow_instance__status="active",
        )
        for si in overdue:
            pass  # TODO: integrazione notifiche (RF-057)
        return list(overdue)
