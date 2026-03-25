"""
API Dashboard e reportistica (FASE 14).
"""
from dateutil.relativedelta import relativedelta

from django.db.models import Avg, Count, F, Sum
from django.db.models import DurationField, ExpressionWrapper
from django.db.models.functions import TruncMonth
from django.utils import timezone
from rest_framework import status
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


def _user_protocol_ou_ids(user):
    from apps.organizations.models import OrganizationalUnitMembership

    return set(
        OrganizationalUnitMembership.objects.filter(user=user).values_list(
            "organizational_unit_id", flat=True
        )
    )


class DocumentsTrendView(APIView):
    """Serie temporale documenti creati per mese."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        months = int(request.query_params.get("months", 12))
        now = timezone.now()
        start = (now - relativedelta(months=months)).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )

        qs = Document.objects.filter(is_deleted=False, created_at__gte=start)
        if getattr(request.user, "role", None) != "ADMIN":
            qs = qs.filter(_documents_queryset_filter(request.user))

        data = (
            qs.annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )
        return Response(
            {
                "results": [
                    {"month": d["month"].strftime("%Y-%m"), "count": d["count"]}
                    for d in data
                    if d["month"] is not None
                ]
            }
        )


class ProtocolsTrendView(APIView):
    """Protocolli per mese e direzione (in/out)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        months = int(request.query_params.get("months", 12))
        now = timezone.now()
        start = (now - relativedelta(months=months)).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )

        qs = Protocol.objects.filter(created_at__gte=start)
        if getattr(request.user, "role", None) != "ADMIN":
            ou_ids = _user_protocol_ou_ids(request.user)
            if not ou_ids:
                return Response({"results": []})
            qs = qs.filter(organizational_unit_id__in=ou_ids)

        data = (
            qs.annotate(month=TruncMonth("created_at"))
            .values("month", "direction")
            .annotate(count=Count("id"))
            .order_by("month")
        )
        out = []
        for d in data:
            if d["month"] is None:
                continue
            direction = d["direction"] or ""
            label = "IN" if direction in ("in", "IN") else "OUT" if direction in ("out", "OUT") else direction.upper() or "—"
            out.append(
                {
                    "month": d["month"].strftime("%Y-%m"),
                    "direction": label,
                    "count": d["count"],
                }
            )
        return Response({"results": out})


class WorkflowStatsView(APIView):
    """Statistiche workflow (ADMIN, APPROVER, REVIEWER)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        role = getattr(request.user, "role", None)
        if role not in ("ADMIN", "APPROVER", "REVIEWER"):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        this_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        active = WorkflowInstance.objects.filter(status="active").count()
        completed_total = WorkflowInstance.objects.filter(status="completed").count()
        completed_month = WorkflowInstance.objects.filter(
            status="completed", completed_at__gte=this_month
        ).count()
        rejected = WorkflowInstance.objects.filter(status="rejected").count()
        cancelled = WorkflowInstance.objects.filter(status="cancelled").count()

        agg = WorkflowInstance.objects.filter(
            status="completed",
            completed_at__isnull=False,
        ).aggregate(
            avg_dur=Avg(
                ExpressionWrapper(
                    F("completed_at") - F("started_at"),
                    output_field=DurationField(),
                )
            )
        )
        avg_hours = None
        if agg["avg_dur"]:
            avg_hours = round(agg["avg_dur"].total_seconds() / 3600, 1)

        return Response(
            {
                "active": active,
                "completed_total": completed_total,
                "completed_this_month": completed_month,
                "rejected": rejected,
                "cancelled": cancelled,
                "avg_completion_hours": avg_hours,
            }
        )


class StorageTrendView(APIView):
    """Trend consumo storage (somma dimensioni versioni caricate per mese)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        months = int(request.query_params.get("months", 12))
        now = timezone.now()
        start = (now - relativedelta(months=months)).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )

        qs = DocumentVersion.objects.filter(created_at__gte=start)
        if getattr(request.user, "role", None) != "ADMIN":
            doc_ids = Document.objects.filter(is_deleted=False).filter(
                _documents_queryset_filter(request.user)
            ).values_list("id", flat=True)
            qs = qs.filter(document_id__in=doc_ids)

        data = (
            qs.annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(bytes_total=Sum("file_size"))
            .order_by("month")
        )
        return Response(
            {
                "results": [
                    {
                        "month": d["month"].strftime("%Y-%m"),
                        "bytes": d["bytes_total"] or 0,
                        "mb": round((d["bytes_total"] or 0) / (1024 * 1024), 2),
                    }
                    for d in data
                    if d["month"] is not None
                ]
            }
        )


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
