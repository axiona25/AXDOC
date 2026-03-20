"""
API Dashboard e reportistica (FASE 14).
"""
from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.documents.models import Document, DocumentVersion
from apps.documents.permissions import _documents_queryset_filter
from apps.dossiers.models import Dossier
from apps.workflows.models import WorkflowInstance, WorkflowStepInstance
from apps.authentication.models import AuditLog
from apps.notifications.models import Notification
from apps.protocols.models import Protocol


def _documents_qs(user):
    """Documenti accessibili all'utente."""
    return Document.objects.filter(is_deleted=False).filter(_documents_queryset_filter(user))


class DashboardStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        role = getattr(user, "role", None)
        payload = {}

        # Per TUTTI
        my_docs = _documents_qs(user)
        payload["my_documents"] = {
            "total": my_docs.count(),
            "draft": my_docs.filter(status="DRAFT").count(),
            "in_review": my_docs.filter(status="IN_REVIEW").count(),
            "approved": my_docs.filter(status="APPROVED").count(),
            "rejected": my_docs.filter(status="REJECTED").count(),
            "archived": my_docs.filter(status="ARCHIVED").count(),
        }
        payload["my_pending_steps"] = WorkflowStepInstance.objects.filter(
            assigned_to=user,
            status__in=("pending", "in_progress"),
            workflow_instance__status="active",
        ).count()
        payload["unread_notifications"] = Notification.objects.filter(recipient=user, is_read=False).count()

        recent_audit = AuditLog.objects.filter(user=user).select_related("user").order_by("-timestamp")[:10]
        payload["recent_activity"] = [
            {
                "id": str(a.id),
                "user_id": str(a.user_id) if a.user_id else None,
                "user_email": a.user.email if a.user_id else None,
                "action": a.action,
                "detail": a.detail or {},
                "timestamp": a.timestamp.isoformat(),
            }
            for a in recent_audit
        ]

        if role == "ADMIN":
            from django.contrib.auth import get_user_model
            User = get_user_model()
            payload["total_users"] = User.objects.filter(is_active=True).exclude(is_deleted=True).count()
            payload["total_documents"] = Document.objects.filter(is_deleted=False).count()
            payload["total_dossiers"] = {
                "open": Dossier.objects.filter(is_deleted=False).exclude(status="archived").count(),
                "archived": Dossier.objects.filter(is_deleted=False, status="archived").count(),
            }
            this_month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            payload["total_protocols"] = {
                "count": Protocol.objects.count(),
                "this_month": Protocol.objects.filter(created_at__gte=this_month_start).count(),
            }
            payload["documents_by_status"] = dict(
                Document.objects.filter(is_deleted=False).values("status").annotate(c=Count("id")).values_list("status", "c")
            )
            payload["active_workflows"] = WorkflowInstance.objects.filter(status="active").count()
            storage = DocumentVersion.objects.aggregate(s=Sum("file_size"))["s"] or 0
            payload["storage_used_mb"] = round(storage / (1024 * 1024), 2)

        if role in ("APPROVER", "REVIEWER"):
            pending_wi = WorkflowStepInstance.objects.filter(
                assigned_to=user,
                status__in=("pending", "in_progress"),
                workflow_instance__status="active",
            )
            payload["pending_approvals"] = pending_wi.count()
            payload["dossiers_responsible"] = Dossier.objects.filter(is_deleted=False, responsible=user).count()

        return Response(payload)


class RecentDocumentsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = _documents_qs(request.user).select_related(
            "created_by", "folder"
        ).order_by("-updated_at")[:10]
        return Response({
            "results": [
                {
                    "id": str(d.id),
                    "title": d.title,
                    "status": d.status,
                    "updated_at": d.updated_at.isoformat(),
                    "created_by_id": str(d.created_by_id) if d.created_by_id else None,
                    "created_by_email": d.created_by.email if d.created_by_id else None,
                    "folder_name": d.folder.name if d.folder_id else None,
                }
                for d in qs
            ]
        })


class MyTasksView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        step_instances = WorkflowStepInstance.objects.filter(
            assigned_to=user,
            status__in=("pending", "in_progress"),
            workflow_instance__status="active",
        ).select_related(
            "workflow_instance", "workflow_instance__document", "step"
        ).order_by("deadline")
        results = []
        for si in step_instances:
            wi = si.workflow_instance
            doc = wi.document
            results.append({
                "step_instance_id": str(si.id),
                "workflow_instance_id": str(wi.id),
                "document_id": str(doc.id),
                "document_title": doc.title,
                "step_name": si.step.name,
                "step_action": si.step.action,
                "status": si.status,
                "deadline": si.deadline.isoformat() if si.deadline else None,
                "started_at": si.started_at.isoformat() if si.started_at else None,
            })
        return Response({"results": results})
