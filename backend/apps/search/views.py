"""
API Ricerca full-text e avanzata (FASE 12, RF-070..RF-074, FASE 37 multi-tipo).
"""
from django.db.models import Count, Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.documents.models import Document
from apps.documents.permissions import _documents_queryset_filter
from .serializers import SearchResultSerializer
from .models import DocumentIndex


_VALID_SEARCH_TYPES = frozenset({"all", "documents", "protocols", "dossiers", "contacts"})


class SearchView(APIView):
    permission_classes = [IsAuthenticated]

    def _effective_tenant(self, request):
        """
        Tenant coerente con l'utente JWT/sessione.
        Il TenantMiddleware gira prima dell'autenticazione DRF: request.tenant può essere
        solo il tenant 'default' o dal claim JWT, mentre request.user.tenant_id è corretto
        solo dopo la view. Per protocolli/fascicoli usare sempre il tenant dell'utente.
        """
        from apps.organizations.models import Tenant

        user = getattr(request, "user", None)
        if user is not None and getattr(user, "is_authenticated", False):
            uid = getattr(user, "tenant_id", None)
            if uid:
                t = Tenant.objects.filter(id=uid, is_active=True).first()
                if t:
                    return t
        return getattr(request, "tenant", None)

    def get(self, request):
        q = (request.query_params.get("q") or "").strip()
        search_type = request.query_params.get("type", "all")
        folder_id = request.query_params.get("folder_id")
        metadata_structure_id = request.query_params.get("metadata_structure_id")
        status_filter = request.query_params.get("status")
        created_by = request.query_params.get("created_by")
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        order_by = request.query_params.get("order_by", "-updated_at")
        try:
            page_size_raw = int(request.query_params.get("page_size", 20))
        except (TypeError, ValueError):
            page_size_raw = 20
        page_size = max(1, min(page_size_raw, 100))
        try:
            page = int(request.query_params.get("page", 1))
        except (TypeError, ValueError):
            page = 1
        if page < 1:
            page = 1

        if search_type not in _VALID_SEARCH_TYPES:
            return Response({"results": [], "total_count": 0, "facets": {}, "type": search_type})

        if search_type == "all":
            if not q:
                return self._response_documents_only(
                    request,
                    q,
                    page,
                    page_size,
                    folder_id,
                    metadata_structure_id,
                    status_filter,
                    created_by,
                    date_from,
                    date_to,
                    order_by,
                    response_type="all",
                )
            return self._response_all_types(request, q, page_size)

        if search_type == "documents":
            return self._response_documents_only(
                request,
                q,
                page,
                page_size,
                folder_id,
                metadata_structure_id,
                status_filter,
                created_by,
                date_from,
                date_to,
                order_by,
                response_type="documents",
            )

        if search_type == "protocols":
            return self._response_single_protocols(request, q, page, page_size)

        if search_type == "dossiers":
            return self._response_single_dossiers(request, q, page, page_size)

        if search_type == "contacts":
            return self._response_single_contacts(request, q, page, page_size)

        return Response({"results": [], "total_count": 0, "facets": {}, "type": search_type})  # pragma: no cover

    def _response_documents_only(
        self,
        request,
        q,
        page,
        page_size,
        folder_id,
        metadata_structure_id,
        status_filter,
        created_by,
        date_from,
        date_to,
        order_by,
        response_type="documents",
    ):
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
            "type": response_type,
        })

    def _response_all_types(self, request, q, page_size):
        per = min(5, page_size)
        doc_results, doc_count = self._search_documents_slice(request, q, per, 0)
        proto_results, proto_count = self._search_protocols_slice(request, q, per, 0)
        dos_results, dos_count = self._search_dossiers_slice(request, q, per, 0)
        cont_results, cont_count = self._search_contacts_slice(request, q, per, 0)

        results = doc_results + proto_results + dos_results + cont_results
        total_count = doc_count + proto_count + dos_count + cont_count
        facets = {
            "documents": doc_count,
            "protocols": proto_count,
            "dossiers": dos_count,
            "contacts": cont_count,
        }
        return Response({
            "results": results,
            "total_count": total_count,
            "facets": facets,
            "type": "all",
        })

    def _search_documents_slice(self, request, q, limit, offset):
        qs = Document.objects.filter(is_deleted=False).filter(
            _documents_queryset_filter(request.user)
        ).distinct()
        if q:
            title_match = Q(title__icontains=q)
            index_match = Q(search_index__content__icontains=q)
            qs = qs.filter(title_match | index_match).distinct()
        count = qs.count()
        items = list(
            qs.select_related("folder")
            .prefetch_related("search_index")
            .order_by("-updated_at")[offset : offset + limit]
        )
        for doc in items:
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
            else:  # pragma: no cover — _response_all_types passa sempre q non vuoto
                setattr(doc, "_search_snippet", (doc.description or "")[:300])
        ser = SearchResultSerializer(items, many=True).data
        out = []
        for row in ser:
            row = dict(row)
            row["type"] = "document"
            row["subtitle"] = row.get("folder_name") or ""
            row["url"] = f"/documents?doc={row['id']}"
            out.append(row)
        return out, count

    def _protocol_queryset(self, request):
        from apps.protocols.models import Protocol
        from apps.users.permissions import get_user_ou_ids

        qs = Protocol.objects.all()
        if getattr(request.user, "is_superuser", False):
            return qs
        tenant = self._effective_tenant(request)
        if tenant and hasattr(Protocol, "tenant"):
            if getattr(tenant, "slug", None) == "default":
                qs = qs.filter(Q(tenant=tenant) | Q(tenant__isnull=True))
            else:
                qs = qs.filter(tenant=tenant)
        if getattr(request.user, "role", None) == "ADMIN":
            return qs
        ou_ids = get_user_ou_ids(request.user)
        if not ou_ids:
            return qs.none()
        return qs.filter(organizational_unit_id__in=ou_ids)

    def _search_protocols_slice(self, request, q, limit, offset):
        from apps.protocols.models import ProtocolAttachment

        if getattr(request.user, "user_type", "internal") == "guest":
            return [], 0
        if not q:  # pragma: no cover — le view pubbliche escludono q vuoto prima della slice
            return [], 0

        qs_p = self._protocol_queryset(request)
        att_idx_ids = DocumentIndex.objects.filter(content__icontains=q).values_list("document_id", flat=True)
        att_title_ids = Document.objects.filter(title__icontains=q).values_list("id", flat=True)
        att_doc_ids = set(att_idx_ids) | set(att_title_ids)
        protocol_ids_from_attachments = []
        if att_doc_ids:
            protocol_ids_from_attachments = ProtocolAttachment.objects.filter(
                document_id__in=att_doc_ids,
                protocol_id__in=qs_p.values_list("id", flat=True),
            ).values_list("protocol_id", flat=True)

        qs = qs_p.filter(
            Q(subject__icontains=q)
            | Q(sender_receiver__icontains=q)
            | Q(protocol_id__icontains=q)
            | Q(notes__icontains=q)
            | Q(description__icontains=q)
            | Q(id__in=protocol_ids_from_attachments)
        )
        count = qs.count()
        items = list(
            qs.select_related("organizational_unit", "created_by").order_by("-created_at")[offset : offset + limit]
        )
        results = []
        for p in items:
            _pp = [x for x in (p.protocol_id, p.subject) if x]
            title = " — ".join(_pp) if _pp else str(p.id)
            subtitle = p.organizational_unit.name if p.organizational_unit_id else ""
            results.append({
                "id": str(p.id),
                "type": "protocol",
                "title": title,
                "subtitle": subtitle,
                "status": getattr(p, "status", "") or "",
                "updated_at": p.created_at.isoformat() if p.created_at else "",
                "url": f"/protocols/{p.id}",
                "snippet": (p.notes or "")[:150],
                "description": "",
                "folder_name": None,
                "score": None,
            })
        return results, count

    def _dossier_queryset(self, request):
        from apps.dossiers.models import Dossier
        from apps.users.permissions import get_user_ou_ids

        qs = Dossier.objects.filter(is_deleted=False)
        if getattr(request.user, "is_superuser", False):
            return qs
        tenant = self._effective_tenant(request)
        if tenant and hasattr(Dossier, "tenant"):
            if getattr(tenant, "slug", None) == "default":
                qs = qs.filter(Q(tenant=tenant) | Q(tenant__isnull=True))
            else:
                qs = qs.filter(tenant=tenant)
        if getattr(request.user, "role", None) == "ADMIN":
            return qs
        user = request.user
        user_ou_ids = get_user_ou_ids(user)
        if not user_ou_ids:
            return qs.none()
        return qs.filter(
            Q(responsible=user)
            | Q(created_by=user)
            | Q(user_permissions__user=user, user_permissions__can_read=True)
            | Q(
                ou_permissions__organizational_unit_id__in=user_ou_ids,
                ou_permissions__can_read=True,
            )
            | Q(organizational_unit_id__in=user_ou_ids)
        ).distinct()

    def _search_dossiers_slice(self, request, q, limit, offset):
        from apps.dossiers.models import DossierDocument, DossierEmail

        if getattr(request.user, "user_type", "internal") == "guest":
            return [], 0
        if not q:  # pragma: no cover — le view pubbliche escludono q vuoto prima della slice
            return [], 0

        qs_d = self._dossier_queryset(request)

        idx_doc_ids = DocumentIndex.objects.filter(content__icontains=q).values_list("document_id", flat=True)
        title_doc_ids = Document.objects.filter(title__icontains=q).values_list("id", flat=True)
        doc_ids = set(idx_doc_ids) | set(title_doc_ids)
        dossier_ids_from_docs = []
        if doc_ids:
            dossier_ids_from_docs = DossierDocument.objects.filter(
                document_id__in=doc_ids,
                dossier_id__in=qs_d.values_list("id", flat=True),
            ).values_list("dossier_id", flat=True)

        dossier_ids_from_email = DossierEmail.objects.filter(
            Q(subject__icontains=q) | Q(body__icontains=q) | Q(from_address__icontains=q),
            dossier_id__in=qs_d.values_list("id", flat=True),
        ).values_list("dossier_id", flat=True).distinct()

        qs = qs_d.filter(
            Q(title__icontains=q)
            | Q(identifier__icontains=q)
            | Q(description__icontains=q)
            | Q(id__in=dossier_ids_from_docs)
            | Q(id__in=dossier_ids_from_email)
        )
        count = qs.count()
        items = list(
            qs.select_related("responsible", "organizational_unit").order_by("-updated_at")[offset : offset + limit]
        )
        results = []
        for d in items:
            _dp = [x for x in (d.identifier, d.title) if x]
            title = " — ".join(_dp) if _dp else str(d.id)
            sub = ""
            if d.responsible_id:
                sub = d.responsible.get_full_name() or d.responsible.email or ""
            results.append({
                "id": str(d.id),
                "type": "dossier",
                "title": title,
                "subtitle": sub,
                "status": d.status,
                "updated_at": d.updated_at.isoformat() if d.updated_at else "",
                "url": f"/dossiers/{d.id}",
                "snippet": (d.description or "")[:150],
                "description": "",
                "folder_name": None,
                "score": None,
            })
        return results, count

    def _contact_queryset(self, request):
        from apps.contacts.models import Contact

        qs = Contact.objects.all()
        user = request.user
        if getattr(user, "role", None) != "ADMIN":
            qs = qs.filter(Q(is_shared=True) | Q(created_by=user))
        return qs

    def _search_contacts_slice(self, request, q, limit, offset):
        if not q:  # pragma: no cover — _response_single_contacts esclude q vuoto
            return [], 0
        qs = self._contact_queryset(request)
        q_filter = (
            Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(company_name__icontains=q)
        )
        if "@" in q:
            q_filter |= Q(email=q) | Q(pec=q)
        qs = qs.filter(q_filter)
        count = qs.count()
        items = list(qs.order_by("last_name", "first_name")[offset : offset + limit])
        results = []
        for c in items:
            results.append({
                "id": str(c.id),
                "type": "contact",
                "title": str(c),
                "subtitle": c.company_name or "",
                "status": "",
                "updated_at": c.updated_at.isoformat() if c.updated_at else "",
                "url": f"/contacts/{c.id}",
                "snippet": "",
                "description": "",
                "folder_name": None,
                "score": None,
            })
        return results, count

    def _response_single_protocols(self, request, q, page, page_size):
        if getattr(request.user, "user_type", "internal") == "guest":
            return Response({"results": [], "total_count": 0, "facets": {}, "type": "protocols"})
        if not q:
            return Response({"results": [], "total_count": 0, "facets": {}, "type": "protocols"})
        offset = (page - 1) * page_size
        results, total = self._search_protocols_slice(request, q, page_size, offset)
        return Response({
            "results": results,
            "total_count": total,
            "facets": {"protocols": total},
            "type": "protocols",
        })

    def _response_single_dossiers(self, request, q, page, page_size):
        if getattr(request.user, "user_type", "internal") == "guest":
            return Response({"results": [], "total_count": 0, "facets": {}, "type": "dossiers"})
        if not q:
            return Response({"results": [], "total_count": 0, "facets": {}, "type": "dossiers"})
        offset = (page - 1) * page_size
        results, total = self._search_dossiers_slice(request, q, page_size, offset)
        return Response({
            "results": results,
            "total_count": total,
            "facets": {"dossiers": total},
            "type": "dossiers",
        })

    def _response_single_contacts(self, request, q, page, page_size):
        if not q:
            return Response({"results": [], "total_count": 0, "facets": {}, "type": "contacts"})
        offset = (page - 1) * page_size
        results, total = self._search_contacts_slice(request, q, page_size, offset)
        return Response({
            "results": results,
            "total_count": total,
            "facets": {"contacts": total},
            "type": "contacts",
        })
