"""
Servizio notifiche (RF-057, FASE 12).
"""
from django.utils import timezone
from .models import Notification


class NotificationService:
    @staticmethod
    def _tenant_id(recipient=None, document=None):
        if document and getattr(document, "tenant_id", None):
            return document.tenant_id
        if recipient and getattr(recipient, "tenant_id", None):
            return recipient.tenant_id
        try:
            from apps.organizations.middleware import get_current_tenant

            t = get_current_tenant()
            return t.id if t else None
        except Exception:
            return None

    @staticmethod
    def send(recipient, notification_type, title, body, link_url="", metadata=None, document=None):
        tid = NotificationService._tenant_id(recipient=recipient, document=document)
        kw = dict(
            recipient=recipient,
            notification_type=notification_type,
            title=title,
            body=body,
            link_url=link_url or "",
            metadata=metadata or {},
        )
        if tid:
            kw["tenant_id"] = tid
        return Notification.objects.create(**kw)

    @staticmethod
    def send_bulk(recipients, notification_type, title, body, link_url="", metadata=None, document=None):
        return [
            NotificationService.send(
                r,
                notification_type,
                title,
                body,
                link_url=link_url,
                metadata=metadata,
                document=document,
            )
            for r in recipients
        ]

    @staticmethod
    def notify_workflow_assigned(step_instance):
        """Notifica agli assegnatari dello step."""
        doc = step_instance.workflow_instance.document
        title = f"Workflow assegnato: {doc.title}"
        body = f"Ti è stato assegnato lo step «{step_instance.step.name}» per il documento «{doc.title}»."
        link_url = f"/documents/{doc.id}"
        metadata = {
            "document_id": str(doc.id),
            "workflow_instance_id": str(step_instance.workflow_instance.id),
            "step_name": step_instance.step.name,
        }
        assignees = list(step_instance.assigned_to.all())
        if assignees:
            NotificationService.send_bulk(
                assignees,
                "workflow_assigned",
                title,
                body,
                link_url=link_url,
                metadata=metadata,
                document=doc,
            )

    @staticmethod
    def notify_workflow_completed(instance):
        """Notifica a started_by che il workflow è completato."""
        if not instance.started_by_id:
            return
        doc = instance.document
        title = "Workflow completato"
        body = f"Il workflow sul documento «{doc.title}» è stato completato e il documento è approvato."
        link_url = f"/documents/{doc.id}"
        NotificationService.send(
            instance.started_by,
            "workflow_completed",
            title,
            body,
            link_url=link_url,
            metadata={"document_id": str(doc.id), "workflow_instance_id": str(instance.id)},
            document=doc,
        )

    @staticmethod
    def notify_workflow_rejected(instance, comment):
        """Notifica a started_by che il workflow è stato rifiutato."""
        if not instance.started_by_id:
            return
        doc = instance.document
        title = "Documento rifiutato"
        body = f"Il documento «{doc.title}» è stato rifiutato nel workflow. Commento: {comment[:200] if comment else '—'}"
        link_url = f"/documents/{doc.id}"
        NotificationService.send(
            instance.started_by,
            "workflow_rejected",
            title,
            body,
            link_url=link_url,
            metadata={"document_id": str(doc.id), "comment": comment},
            document=doc,
        )

    @staticmethod
    def notify_changes_requested(instance, comment):
        """Notifica al creatore del documento che sono richieste modifiche."""
        doc = instance.document
        creator = doc.created_by
        if not creator:
            return
        title = "Modifiche richieste"
        body = f"Sono state richieste modifiche per il documento «{doc.title}». Commento: {comment[:200] if comment else '—'}"
        link_url = f"/documents/{doc.id}"
        NotificationService.send(
            creator,
            "workflow_changes_requested",
            title,
            body,
            link_url=link_url,
            metadata={"document_id": str(doc.id), "comment": comment},
            document=doc,
        )

    @staticmethod
    def notify_document_shared(document, shared_with_user, shared_by):
        """Notifica all'utente con cui è stato condiviso il documento."""
        title = "Documento condiviso con te"
        shared_by_name = getattr(shared_by, "email", str(shared_by))
        if getattr(shared_by, "first_name", None) or getattr(shared_by, "last_name", None):
            shared_by_name = f"{getattr(shared_by, 'first_name', '')} {getattr(shared_by, 'last_name', '')}".strip()
        body = f"{shared_by_name} ha condiviso il documento «{document.title}» con te."
        link_url = f"/documents/{document.id}"
        NotificationService.send(
            shared_with_user,
            "document_shared",
            title,
            body,
            link_url=link_url,
            metadata={"document_id": str(document.id), "shared_by_id": str(shared_by.id)},
            document=document,
        )
