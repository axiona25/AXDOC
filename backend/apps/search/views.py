"""
API Ricerca full-text e avanzata (FASE 12, RF-070..RF-074).
"""
from django.db.models import Q
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.documents.models import Document
from apps.documents.permissions import _documents_queryset_filter
from .serializers import SearchResultSerializer
from .models import DocumentIndex


class SearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        q = (request.query_params.get("q") or "").strip()
        search_type = request.query_params.get("type", "documents")
        folder_id = request.query_params.get("folder_id")
        metadata_structure_id = request.query_params.get("metadata_structure_id")
        status_filter = request.query_params.get("status")
        created_by = request.query_params.get("created_by")
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        order_by = request.query_params.get("order_by", "-updated_at")
        page_size = min(int(request.query_params.get("page_size", 20)), 100)
        page = int(request.query_params.get("page", 1))
        if page < 1:
            page = 1

        if search_type != "documents":
            return Response({"results": [], "total_count": 0, "facets": {}})

        qs = Document.objects.filter(is_deleted=False).filter(
            _documents_queryset_filter(request.user)
        ).distinct()

        if folder_id:
            qs = qs.filter(folder_id=folder_id)
        if metadata_structure_id:
            qs = qs.filter(metadata_structure_id=metadata_structure_id)
        if status_filter:
            qs = qs.filter(status=status_filter)
        if created_by:
            qs = qs.filter(created_by_id=created_by)
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        for key, value in request.query_params.items():
            if key.startswith("metadata_") and key != "metadata_structure_id" and value:
                field_name = key.replace("metadata_", "", 1)
                qs = qs.filter(**{f"metadata_values__{field_name}__icontains": value})

        if q:
            title_match = Q(title__icontains=q)
            index_match = Q(search_index__content__icontains=q)
            qs = qs.filter(title_match | index_match).distinct()

        if order_by == "relevance" and q:
            qs = qs.order_by("-updated_at")
        elif order_by and order_by.lstrip("-") in ("title", "created_at", "updated_at"):
            qs = qs.order_by(order_by)
        else:
            qs = qs.order_by("-updated_at")

        total_count = qs.count()
        start = (page - 1) * page_size
        page_qs = list(qs.select_related("folder").prefetch_related("search_index")[start : start + page_size])
        for doc in page_qs:
            if q:
                snippet = ""
                idx = getattr(doc, "search_index", None)
                if idx and getattr(idx, "content", None) and q.lower() in (idx.content or "").lower():
                    pos = (idx.content or "").lower().find(q.lower())
                    s, e = max(0, pos - 80), min(len(idx.content or ""), pos + len(q) + 80)
                    snippet = "..." + (idx.content or "")[s:e] + "..."
                if not snippet and doc.title and q.lower() in (doc.title or "").lower():
                    snippet = doc.title or ""
                setattr(doc, "_search_snippet", snippet or (doc.description or "")[:200])
                setattr(doc, "_search_score", 1 if (doc.title and q.lower() in (doc.title or "").lower()) else 0)
            else:
                setattr(doc, "_search_snippet", (doc.description or "")[:300])
                setattr(doc, "_search_score", None)
        facets = {}
        try:
            from django.db.models import Count
            status_counts = Document.objects.filter(
                _documents_queryset_filter(request.user),
                is_deleted=False,
            ).values("status").annotate(count=Count("id"))
            facets["status"] = {x["status"]: x["count"] for x in status_counts}
        except Exception:
            pass

        return Response({
            "results": SearchResultSerializer(page_qs, many=True).data,
            "total_count": total_count,
            "facets": facets,
        })
