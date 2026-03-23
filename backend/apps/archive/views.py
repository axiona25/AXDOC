"""
API Archivio e conservazione AGID (FASE 21).
"""
import io
from django.db.models import Q
from django.utils import timezone
from django.http import HttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from .models import DocumentArchive, RetentionRule, InformationPackage, PackageDocument, PackageProtocolLink, PackageDossierLink
from .serializers import DocumentArchiveSerializer, RetentionRuleSerializer, InformationPackageSerializer
from .packager import AgidPackager
from .classification import TITOLARIO_DEFAULT


def _is_admin_or_approver(user):
    return getattr(user, "role", None) in ("ADMIN", "APPROVER")


def _is_admin(user):
    return getattr(user, "role", None) == "ADMIN"


class DocumentArchiveViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DocumentArchiveSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = DocumentArchive.objects.select_related("document", "archive_by", "historical_by")
        stage = self.request.query_params.get("stage")
        if stage:
            qs = qs.filter(stage=stage)
        if not _is_admin(self.request.user) and not _is_admin_or_approver(self.request.user):
            from apps.users.permissions import get_user_ou_ids
            from apps.organizations.models import OrganizationalUnitMembership

            user_ou_ids = get_user_ou_ids(self.request.user)
            user_ou_member_ids = list(
                OrganizationalUnitMembership.objects.filter(
                    organizational_unit_id__in=user_ou_ids, is_active=True
                )
                .values_list("user_id", flat=True)
                .distinct()
            )
            qs = qs.filter(
                Q(document__created_by=self.request.user)
                | Q(document__owner=self.request.user)
                | Q(
                    document__owner_id__in=user_ou_member_ids,
                    document__visibility="office",
                )
            )
        return qs.order_by("-updated_at")

    @action(detail=True, methods=["post"], url_path="move_to_deposit")
    def move_to_deposit(self, request, pk=None):
        """Sposta in Archivio di Deposito. Solo ADMIN/APPROVER."""
        if not _is_admin_or_approver(request.user):
            return Response({"detail": "Non autorizzato."}, status=status.HTTP_403_FORBIDDEN)
        rec = self.get_object()
        if rec.stage != "current":
            return Response({"detail": "Solo documenti in Archivio Corrente."}, status=status.HTTP_400_BAD_REQUEST)
        rec.stage = "deposit"
        rec.archive_date = timezone.now()
        rec.archive_by = request.user
        rec.notes = (rec.notes or "") + "\n" + (request.data.get("notes") or "")
        rec.save(update_fields=["stage", "archive_date", "archive_by", "notes", "updated_at"])
        return Response(DocumentArchiveSerializer(rec).data)

    @action(detail=True, methods=["post"], url_path="move_to_historical")
    def move_to_historical(self, request, pk=None):
        """Sposta in Archivio Storico. Solo ADMIN."""
        if not _is_admin(request.user):
            return Response({"detail": "Solo ADMIN."}, status=status.HTTP_403_FORBIDDEN)
        rec = self.get_object()
        if rec.stage != "deposit":
            return Response({"detail": "Solo documenti in Archivio di Deposito."}, status=status.HTTP_400_BAD_REQUEST)
        rec.stage = "historical"
        rec.historical_date = timezone.now()
        rec.historical_by = request.user
        rec.notes = (rec.notes or "") + "\n" + (request.data.get("notes") or "")
        rec.save(update_fields=["stage", "historical_date", "historical_by", "notes", "updated_at"])
        return Response(DocumentArchiveSerializer(rec).data)

    @action(detail=True, methods=["post"], url_path="request_discard")
    def request_discard(self, request, pk=None):
        """Richiedi scarto. Solo ADMIN."""
        if not _is_admin(request.user):
            return Response({"detail": "Solo ADMIN."}, status=status.HTTP_403_FORBIDDEN)
        rec = self.get_object()
        rec.discard_date = timezone.now().date()
        rec.save(update_fields=["discard_date", "updated_at"])
        return Response(DocumentArchiveSerializer(rec).data)

    @action(detail=True, methods=["post"], url_path="approve_discard")
    def approve_discard(self, request, pk=None):
        """Approva scarto. Solo ADMIN."""
        if not _is_admin(request.user):
            return Response({"detail": "Solo ADMIN."}, status=status.HTTP_403_FORBIDDEN)
        rec = self.get_object()
        rec.discard_approved = True
        rec.save(update_fields=["discard_approved", "updated_at"])
        return Response(DocumentArchiveSerializer(rec).data)


class InformationPackageViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = InformationPackageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return InformationPackage.objects.select_related("created_by").prefetch_related(
            "documents", "protocols", "dossiers"
        ).order_by("-created_at")

    @action(detail=False, methods=["post"], url_path="create_pdv")
    def create_pdv(self, request):
        """Crea pacchetto PdV. Body: document_ids, protocol_ids, dossier_ids."""
        if not _is_admin_or_approver(request.user):
            return Response({"detail": "Non autorizzato."}, status=status.HTTP_403_FORBIDDEN)
        from apps.documents.models import Document
        from apps.protocols.models import Protocol
        from apps.dossiers.models import Dossier
        doc_ids = request.data.get("document_ids") or []
        proto_ids = request.data.get("protocol_ids") or []
        dossier_ids = request.data.get("dossier_ids") or []
        if not doc_ids and not proto_ids and not dossier_ids:
            return Response({"detail": "Fornire almeno document_ids, protocol_ids o dossier_ids."}, status=status.HTTP_400_BAD_REQUEST)
        package_id = f"PdV-{timezone.now().strftime('%Y%m%d-%H%M%S')}"
        pkg = InformationPackage.objects.create(
            package_type="PdV",
            package_id=package_id,
            created_by=request.user,
            status="draft",
        )
        documents = list(Document.objects.filter(id__in=doc_ids))
        protocols = list(Protocol.objects.filter(id__in=proto_ids))
        dossiers = list(Dossier.objects.filter(id__in=dossier_ids))
        packager = AgidPackager()
        zip_bytes, manifest = packager.generate_pdv(documents, protocols, dossiers)
        import hashlib
        checksum = hashlib.sha256(zip_bytes).hexdigest()
        from django.core.files.base import ContentFile
        pkg.package_file.save(f"{package_id}.zip", ContentFile(zip_bytes), save=True)
        pkg.manifest_file.save(f"{package_id}_manifest.json", ContentFile(__import__("json").dumps(manifest, indent=2)), save=True)
        pkg.checksum = checksum
        pkg.status = "ready"
        pkg.save(update_fields=["checksum", "status"])
        for d in documents:
            PackageDocument.objects.get_or_create(package=pkg, document=d, defaults={"metadata_snapshot": {}})
        for pr in protocols:
            PackageProtocolLink.objects.get_or_create(package=pkg, protocol=pr)
        for ds in dossiers:
            PackageDossierLink.objects.get_or_create(package=pkg, dossier=ds)
        return Response(InformationPackageSerializer(pkg).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="send_to_conservator")
    def send_to_conservator(self, request, pk=None):
        """Invia al conservatore. Mock: simula accettazione."""
        if not _is_admin_or_approver(request.user):
            return Response({"detail": "Non autorizzato."}, status=status.HTTP_403_FORBIDDEN)
        pkg = self.get_object()
        pkg.conservation_response = {"mock": True, "accepted_at": timezone.now().isoformat()}
        pkg.status = "accepted"
        pkg.save(update_fields=["conservation_response", "status"])
        return Response(InformationPackageSerializer(pkg).data)

    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, pk=None):
        """Scarica il pacchetto ZIP."""
        pkg = self.get_object()
        if not pkg.package_file:
            return Response({"detail": "File non disponibile."}, status=status.HTTP_404_NOT_FOUND)
        try:
            pkg.package_file.open("rb")
            content = pkg.package_file.read()
            pkg.package_file.close()
        except (ValueError, OSError):
            return Response({"detail": "File non disponibile."}, status=status.HTTP_404_NOT_FOUND)
        response = HttpResponse(content, content_type="application/zip")
        response["Content-Disposition"] = f'attachment; filename="{pkg.package_id}.zip"'
        return response

    @action(detail=True, methods=["get"], url_path="generate_pdd")
    def generate_pdd(self, request, pk=None):
        """Genera PdD (Pacchetto di Distribuzione)."""
        if not _is_admin_or_approver(request.user):
            return Response({"detail": "Non autorizzato."}, status=status.HTTP_403_FORBIDDEN)
        pkg = self.get_object()
        packager = AgidPackager()
        pdd_bytes = packager.generate_pdd(pkg)
        response = HttpResponse(pdd_bytes, content_type="application/zip")
        response["Content-Disposition"] = f'attachment; filename="PdD-{pkg.package_id}.zip"'
        return response


class RetentionRuleViewSet(viewsets.ModelViewSet):
    serializer_class = RetentionRuleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if not _is_admin(self.request.user):
            return RetentionRule.objects.none()
        return RetentionRule.objects.all().order_by("classification_code")

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()


class TitolarioTreeView(APIView):
    """GET /api/archive/titolario/ — albero titolario (da RetentionRule + default)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        rules = {r.classification_code: RetentionRuleSerializer(r).data for r in RetentionRule.objects.filter(is_active=True)}
        tree = []
        for node in TITOLARIO_DEFAULT:
            entry = {"code": node["code"], "label": node["label"], "children": []}
            for ch in node.get("children", []):
                c = dict(ch)
                c["rule"] = rules.get(ch["code"])
                entry["children"].append(c)
            tree.append(entry)
        return Response(tree)


class TitolarioDetailView(APIView):
    """GET /api/archive/titolario/<code>/ — regola per codice."""
    permission_classes = [IsAuthenticated]

    def get(self, request, code):
        rule = RetentionRule.objects.filter(classification_code=code, is_active=True).first()
        if not rule:
            return Response({"detail": "Non trovato."}, status=status.HTTP_404_NOT_FOUND)
        return Response(RetentionRuleSerializer(rule).data)
