"""
API documenti: CRUD, versioning, lock, allegati, cifratura (FASE 04 + FASE 05).
"""
import hashlib
import os
from django.http import FileResponse
from django.core.files import File
from django.core.files.base import ContentFile
from django.db.models import Max, Q
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import (
    Document,
    DocumentVersion,
    DocumentAttachment,
    DocumentPermission,
    DocumentOUPermission,
    Folder,
)
from .serializers import (
    DocumentListSerializer,
    DocumentDetailSerializer,
    DocumentCreateSerializer,
    DocumentVersionSerializer,
    DocumentAttachmentSerializer,
)
from .permissions import CanAccessDocument, _documents_queryset_filter
from .encryption import DocumentEncryption
from apps.authentication.models import AuditLog
from apps.users.permissions import IsAdminRole
from django.contrib.auth import get_user_model

User = get_user_model()


class DocumentViewSet(viewsets.ModelViewSet):
    """
    Documenti: list, retrieve, create, update, destroy, upload_version, download,
    versions, lock, unlock, copy, move, attachments. Encrypt/decrypt (FASE 04).
    """
    permission_classes = [IsAuthenticated, CanAccessDocument]

    def get_queryset(self):
        section = (self.request.query_params.get("section") or "").strip().lower()
        if section == "my_files":
            from apps.organizations.models import OrganizationalUnitMembership
            user_ou_ids = list(
                OrganizationalUnitMembership.objects.filter(user=self.request.user).values_list(
                    "organizational_unit_id", flat=True
                )
            )
            owner_ids_in_my_ou = list(
                OrganizationalUnitMembership.objects.filter(
                    organizational_unit_id__in=user_ou_ids
                ).values_list("user_id", flat=True).distinct()
            )
            qs = Document.objects.filter(is_deleted=False).filter(
                Q(owner=self.request.user)
                | Q(visibility=Document.VISIBILITY_OFFICE, owner_id__in=owner_ids_in_my_ou)
            ).distinct()
            return qs.select_related("folder", "created_by")
        if section == "office":
            from apps.organizations.models import OrganizationalUnitMembership
            user_ou_ids = list(
                OrganizationalUnitMembership.objects.filter(user=self.request.user).values_list(
                    "organizational_unit_id", flat=True
                )
            )
            owner_ids_in_my_ou = list(
                OrganizationalUnitMembership.objects.filter(
                    organizational_unit_id__in=user_ou_ids
                ).values_list("user_id", flat=True).distinct()
            )
            qs = Document.objects.filter(
                is_deleted=False,
                visibility=Document.VISIBILITY_OFFICE,
                owner_id__in=owner_ids_in_my_ou,
            ).distinct()
            return qs.select_related("folder", "created_by")
        qs = Document.objects.filter(is_deleted=False).filter(
            _documents_queryset_filter(self.request.user)
        ).distinct()
        visibility = self.request.query_params.get("visibility")
        if visibility in ("personal", "office", "shared"):
            qs = qs.filter(visibility=visibility)
        return qs.select_related("folder", "created_by")

    def get_serializer_class(self):
        if self.action == "list":
            return DocumentListSerializer
        if self.action == "retrieve":
            return DocumentDetailSerializer
        if self.action in ("create", "update", "partial_update"):
            return DocumentCreateSerializer
        return DocumentListSerializer

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        folder_id = request.query_params.get("folder_id")
        if folder_id and folder_id != "null" and folder_id != "":
            qs = qs.filter(folder_id=folder_id)
        else:
            if folder_id == "null" or request.query_params.get("folder_id") == "":
                qs = qs.filter(folder_id__isnull=True)
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        created_by = request.query_params.get("created_by")
        if created_by:
            qs = qs.filter(created_by_id=created_by)
        title = request.query_params.get("title")
        if title:
            qs = qs.filter(title__icontains=title)
        meta_id = request.query_params.get("metadata_structure_id")
        if meta_id:
            qs = qs.filter(metadata_structure_id=meta_id)
        ordering = request.query_params.get("ordering", "-updated_at")
        if ordering.lstrip("-") in ("title", "created_at", "updated_at", "status"):
            qs = qs.order_by(ordering)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = DocumentListSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response(serializer.data)
        serializer = DocumentListSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = DocumentDetailSerializer(instance, context={"request": request})
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response(
                {"file": "Il file è obbligatorio."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        title = (request.data.get("title") or file_obj.name or "Documento").strip()[:500]
        description = (request.data.get("description") or "").strip()
        folder_id = request.data.get("folder_id")
        folder = None
        if folder_id:
            folder = Folder.objects.filter(is_deleted=False, id=folder_id).first()
        meta_id = request.data.get("metadata_structure_id")
        meta_struct = None
        if meta_id:
            from apps.metadata.models import MetadataStructure
            meta_struct = MetadataStructure.objects.filter(id=meta_id).first()
        metadata_values = request.data.get("metadata_values") or {}
        if isinstance(metadata_values, str):
            import json
            try:
                metadata_values = json.loads(metadata_values) if metadata_values.strip() else {}
            except (ValueError, AttributeError):
                metadata_values = {}
        if meta_struct:
            from apps.metadata.validators import validate_metadata_values
            meta_errors = validate_metadata_values(meta_struct, metadata_values)
            if meta_errors:
                return Response(
                    {"metadata_values": {e["field"]: e["message"] for e in meta_errors}},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        visibility = (request.data.get("visibility") or "personal").strip().lower()
        if visibility not in ("personal", "office", "shared"):
            visibility = "personal"
        doc = Document.objects.create(
            title=title,
            description=description,
            folder=folder,
            metadata_structure=meta_struct,
            metadata_values=metadata_values,
            created_by=request.user,
            owner=request.user,
            visibility=visibility,
        )
        checksum = hashlib.sha256(file_obj.read()).hexdigest()
        file_obj.seek(0)
        version = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name=file_obj.name or "file",
            file_size=file_obj.size,
            file_type=file_obj.content_type or "application/octet-stream",
            checksum=checksum,
            created_by=request.user,
            change_description=(request.data.get("change_description") or "").strip(),
            is_current=True,
        )
        version.file.save(file_obj.name or "file", file_obj, save=True)
        from apps.documents.tasks import process_uploaded_file

        process_uploaded_file.delay(str(version.pk))
        allowed_users = request.data.get("allowed_users")
        if isinstance(allowed_users, str):
            import json
            try:
                allowed_users = json.loads(allowed_users) if allowed_users else []
            except Exception:
                allowed_users = []
        if not isinstance(allowed_users, list):
            allowed_users = []
        for uid in allowed_users:
            u = User.objects.filter(id=uid).first()
            if u:
                DocumentPermission.objects.get_or_create(
                    document=doc,
                    user=u,
                    defaults={"can_read": True, "can_write": False, "can_delete": False},
                )
        allowed_ous = request.data.get("allowed_ous")
        if isinstance(allowed_ous, str):
            import json
            try:
                allowed_ous = json.loads(allowed_ous) if allowed_ous else []
            except Exception:
                allowed_ous = []
        if not isinstance(allowed_ous, list):
            allowed_ous = []
        from apps.organizations.models import OrganizationalUnit
        for ouid in allowed_ous:
            ou = OrganizationalUnit.objects.filter(id=ouid).first()
            if ou:
                DocumentOUPermission.objects.get_or_create(
                    document=doc,
                    organizational_unit=ou,
                    defaults={"can_read": True, "can_write": False},
                )
        AuditLog.log(
            request.user,
            "DOCUMENT_CREATED",
            {"document_id": str(doc.id), "title": doc.title},
            request,
        )
        serializer = DocumentDetailSerializer(doc, context={"request": request})
        response_data = serializer.data
        if not meta_id:
            from apps.metadata.models import MetadataStructure
            if MetadataStructure.objects.filter(is_active=True).filter(applicable_to__contains="document").exists():
                response_data["metadata_required"] = True
        return Response(response_data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        if instance.is_protocolled:
            return Response(
                {"detail": "Documento protocollato non modificabile."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if instance.locked_by_id and instance.locked_by_id != request.user.id and getattr(request.user, "role", None) != "ADMIN":
            return Response(
                {"detail": "Documento bloccato da altro utente."},
                status=status.HTTP_409_CONFLICT,
            )
        can_write = instance.user_permissions.filter(user=request.user, can_write=True).exists()
        if not can_write and instance.created_by_id != request.user.id and getattr(request.user, "role", None) != "ADMIN":
            return Response({"detail": "Non autorizzato a modificare."}, status=status.HTTP_403_FORBIDDEN)
        if "metadata_values" in request.data and instance.metadata_structure_id:
            from apps.metadata.validators import validate_metadata_values
            meta_errors = validate_metadata_values(instance.metadata_structure, request.data.get("metadata_values") or {})
            if meta_errors:
                return Response(
                    {"metadata_values": {e["field"]: e["message"] for e in meta_errors}},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        serializer = DocumentCreateSerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(DocumentDetailSerializer(instance, context={"request": request}).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        can_del = instance.user_permissions.filter(user=request.user, can_delete=True).exists()
        if not can_del and instance.created_by_id != request.user.id and getattr(request.user, "role", None) != "ADMIN":
            return Response({"detail": "Non autorizzato a eliminare."}, status=status.HTTP_403_FORBIDDEN)
        instance.is_deleted = True
        instance.save(update_fields=["is_deleted"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], url_path="my_files_tree")
    def my_files_tree(self, request):
        """
        GET /api/documents/my_files_tree/
        Ritorna: { personal: { folders: [], documents: [] }, office: { folders: [], documents: [] } }
        """
        from apps.organizations.models import OrganizationalUnitMembership
        from .serializers import DocumentListSerializer
        from .folder_views import FolderListSerializer

        user = request.user
        user_ou_ids = list(
            OrganizationalUnitMembership.objects.filter(user=user).values_list(
                "organizational_unit_id", flat=True
            )
        )
        owner_ids_in_my_ou = list(
            OrganizationalUnitMembership.objects.filter(
                organizational_unit_id__in=user_ou_ids
            ).values_list("user_id", flat=True).distinct()
        )

        personal_docs = Document.objects.filter(
            is_deleted=False, owner=user
        ).distinct()
        office_docs = Document.objects.filter(
            is_deleted=False,
            visibility=Document.VISIBILITY_OFFICE,
            owner_id__in=owner_ids_in_my_ou,
        ).distinct()

        personal_folder_ids = set(
            personal_docs.exclude(folder_id__isnull=True).values_list("folder_id", flat=True)
        )
        office_folder_ids = set(
            office_docs.exclude(folder_id__isnull=True).values_list("folder_id", flat=True)
        )
        personal_folders = Folder.objects.filter(
            id__in=personal_folder_ids, is_deleted=False
        ) | Folder.objects.filter(created_by=user, is_deleted=False)
        personal_folders = personal_folders.distinct()
        office_folders = Folder.objects.filter(
            id__in=office_folder_ids, is_deleted=False
        ).distinct()

        def serialize_docs(qs):
            return DocumentListSerializer(qs, many=True, context={"request": request}).data

        def serialize_folders(qs):
            return FolderListSerializer(qs, many=True).data

        return Response({
            "personal": {
                "folders": serialize_folders(personal_folders),
                "documents": serialize_docs(personal_docs),
            },
            "office": {
                "folders": serialize_folders(office_folders),
                "documents": serialize_docs(office_docs),
            },
        })

    @action(detail=True, methods=["get"], url_path="viewer_info")
    def viewer_info(self, request, pk=None):
        """
        GET /api/documents/{id}/viewer_info/
        Ritorna: { viewer_type, mime_type, file_name, file_size } senza scaricare il file.
        """
        document = self.get_object()
        version = document.versions.filter(version_number=document.current_version).first()
        if not version:
            return Response(
                {"detail": "Nessuna versione disponibile."},
                status=status.HTTP_404_NOT_FOUND,
            )
        from .viewer import get_viewer_type
        viewer_type = get_viewer_type(version.file_type or "")
        return Response({
            "viewer_type": viewer_type,
            "mime_type": version.file_type or "application/octet-stream",
            "file_name": version.file_name or "document",
            "file_size": version.file_size or 0,
        })

    @action(detail=True, methods=["get"], url_path="preview")
    def preview(self, request, pk=None):
        """
        GET /api/documents/{id}/preview/
        - PDF: Content-Disposition inline
        - Office: converte con LibreOffice → PDF inline
        - Immagini: inline
        - Email .eml: JSON { from, to, subject, date, body_text, body_html, attachments }
        - Testo: JSON { content, language }
        - Video/Audio: 206 Partial Content con range support
        - Generic: 415 con { viewer_type: 'generic' }
        Header X-Viewer-Type con il tipo rilevato.
        """
        from django.http import HttpResponse, HttpResponseNotAllowed, JsonResponse
        from .viewer import get_viewer_type, convert_office_to_pdf, parse_eml

        document = self.get_object()
        version = document.versions.filter(version_number=document.current_version).first()
        if not version or not version.file:
            return Response(
                {"detail": "Nessuna versione o file disponibile."},
                status=status.HTTP_404_NOT_FOUND,
            )

        mime = (version.file_type or "").strip().lower()
        viewer_type = get_viewer_type(mime)

        if viewer_type == "email":
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".eml", delete=False) as tmp:
                for chunk in version.file.chunks():
                    tmp.write(chunk)
                tmp.flush()
                try:
                    data = parse_eml(tmp.name)
                finally:
                    try:
                        os.unlink(tmp.name)
                    except Exception:
                        pass
            resp = Response(data)
            resp["X-Viewer-Type"] = "email"
            return resp

        if viewer_type == "text":
            try:
                content = version.file.read().decode("utf-8", errors="replace")
            except Exception:
                content = ""
            lang = "plain"
            if "json" in mime:
                lang = "json"
            elif "xml" in mime or "html" in mime:
                lang = "xml"
            elif "csv" in mime:
                lang = "csv"
            resp = Response({"content": content, "language": lang})
            resp["X-Viewer-Type"] = "text"
            return resp

        if viewer_type == "generic":
            return Response(
                {"viewer_type": "generic", "detail": "Anteprima non disponibile per questo formato."},
                status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            )

        if viewer_type == "pdf":
            try:
                f = version.file.open("rb")
                response = FileResponse(f, as_attachment=False, filename=version.file_name or "document.pdf")
                response["Content-Disposition"] = "inline; filename=\"%s\"" % (version.file_name or "document.pdf",)
                response["X-Viewer-Type"] = "pdf"
                return response
            except (ValueError, OSError):
                return Response({"detail": "File non disponibile."}, status=status.HTTP_404_NOT_FOUND)

        if viewer_type == "office":
            import tempfile as tf
            with tf.NamedTemporaryFile(suffix=os.path.splitext(version.file_name or "")[1] or ".docx", delete=False) as tmp:
                for chunk in version.file.chunks():
                    tmp.write(chunk)
                tmp.flush()
                try:
                    pdf_path = convert_office_to_pdf(tmp.name)
                    with open(pdf_path, "rb") as pf:
                        content = pf.read()
                    for f in os.listdir(os.path.dirname(pdf_path)):
                        try:
                            os.unlink(os.path.join(os.path.dirname(pdf_path), f))
                        except Exception:
                            pass
                    try:
                        os.rmdir(os.path.dirname(pdf_path))
                    except Exception:
                        pass
                except Exception as e:
                    return Response(
                        {"detail": "Conversione in PDF non disponibile.", "error": str(e)},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE,
                    )
                finally:
                    try:
                        os.unlink(tmp.name)
                    except Exception:
                        pass
            response = HttpResponse(content, content_type="application/pdf")
            response["Content-Disposition"] = "inline; filename=\"converted.pdf\""
            response["X-Viewer-Type"] = "office"
            return response

        if viewer_type in ("image", "video", "audio"):
            try:
                f = version.file.open("rb")
                disposition = "inline"
                response = FileResponse(f, as_attachment=False, filename=version.file_name or "file")
                response["Content-Disposition"] = "%s; filename=\"%s\"" % (disposition, version.file_name or "file")
                response["X-Viewer-Type"] = viewer_type
                return response
            except (ValueError, OSError):
                return Response({"detail": "File non disponibile."}, status=status.HTTP_404_NOT_FOUND)

        try:
            f = version.file.open("rb")
            response = FileResponse(f, as_attachment=False, filename=version.file_name or "file")
            response["Content-Disposition"] = "inline; filename=\"%s\"" % (version.file_name or "file",)
            response["X-Viewer-Type"] = viewer_type
            return response
        except (ValueError, OSError):
            return Response({"detail": "File non disponibile."}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=["patch"], url_path="visibility")
    def update_visibility(self, request, pk=None):
        """PATCH /api/documents/{id}/visibility/ — body: { visibility: 'personal'|'office'|'shared' }"""
        document = self.get_object()
        if document.is_protocolled:
            return Response(
                {"detail": "Documento protocollato non modificabile."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        vis = (request.data.get("visibility") or "").strip().lower()
        if vis not in ("personal", "office", "shared"):
            return Response(
                {"visibility": "Valore non valido. Usare: personal, office, shared."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        document.visibility = vis
        document.save(update_fields=["visibility", "updated_at"])
        return Response(DocumentDetailSerializer(document, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="upload_version")
    def upload_version(self, request, pk=None):
        document = self.get_object()
        if document.is_protocolled:
            return Response(
                {"detail": "Documento protocollato non modificabile."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if document.locked_by_id and document.locked_by_id != request.user.id:
            return Response(
                {"detail": "Documento bloccato da altro utente. Impossibile caricare nuova versione."},
                status=status.HTTP_409_CONFLICT,
            )
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"file": "Il file è obbligatorio."}, status=status.HTTP_400_BAD_REQUEST)
        agg = document.versions.aggregate(max_v=Max("version_number"))
        next_num = (agg.get("max_v") or 0) + 1
        checksum = hashlib.sha256(file_obj.read()).hexdigest()
        file_obj.seek(0)
        document.versions.update(is_current=False)
        new_version = DocumentVersion.objects.create(
            document=document,
            version_number=next_num,
            file_name=file_obj.name or "file",
            file_size=file_obj.size,
            file_type=file_obj.content_type or "application/octet-stream",
            checksum=checksum,
            created_by=request.user,
            change_description=(request.data.get("change_description") or "").strip(),
            is_current=True,
        )
        new_version.file.save(file_obj.name or "file", file_obj, save=True)
        from apps.documents.tasks import process_uploaded_file

        process_uploaded_file.delay(str(new_version.pk))
        document.current_version = next_num
        document.updated_at = timezone.now()
        document.save(update_fields=["current_version", "updated_at"])
        AuditLog.log(
            request.user,
            "DOCUMENT_UPLOADED",
            {"document_id": str(document.id), "version": next_num},
            request,
        )
        try:
            from apps.search.tasks import index_document
            index_document(new_version.id)
        except Exception:
            pass
        return Response(
            DocumentVersionSerializer(new_version).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, pk=None):
        document = self.get_object()
        version_num = request.query_params.get("version")
        if version_num:
            try:
                version_num = int(version_num)
            except (TypeError, ValueError):
                version_num = document.current_version
        else:
            version_num = document.current_version
        version = document.versions.filter(version_number=version_num).first()
        if not version or not version.file:
            return Response({"detail": "Versione non trovata."}, status=status.HTTP_404_NOT_FOUND)
        try:
            f = version.file.open("rb")
            response = FileResponse(f, as_attachment=True, filename=version.file_name or "document")
            AuditLog.log(
                request.user,
                "DOCUMENT_DOWNLOADED",
                {"document_id": str(document.id), "version": version_num},
                request,
            )
            return response
        except (ValueError, OSError):
            return Response({"detail": "File non disponibile."}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=["get"], url_path="versions")
    def versions_list(self, request, pk=None):
        document = self.get_object()
        versions = document.versions.order_by("-version_number")
        return Response(DocumentVersionSerializer(versions, many=True).data)

    @action(detail=True, methods=["post"], url_path="lock")
    def lock(self, request, pk=None):
        document = self.get_object()
        if document.locked_by_id and document.locked_by_id != request.user.id:
            return Response(
                {"detail": "Documento già bloccato da altro utente."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        document.locked_by = request.user
        document.locked_at = timezone.now()
        document.save(update_fields=["locked_by", "locked_at"])
        return Response(DocumentListSerializer(document, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="unlock")
    def unlock(self, request, pk=None):
        document = self.get_object()
        if document.locked_by_id and document.locked_by_id != request.user.id and getattr(request.user, "role", None) != "ADMIN":
            return Response(
                {"detail": "Solo chi ha bloccato o un amministratore può sbloccare."},
                status=status.HTTP_403_FORBIDDEN,
            )
        document.locked_by = None
        document.locked_at = None
        document.save(update_fields=["locked_by", "locked_at"])
        return Response(DocumentListSerializer(document, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="copy")
    def copy(self, request, pk=None):
        document = self.get_object()
        new_title = (request.data.get("new_title") or (document.title + " (copia)")).strip()[:500]
        folder_id = request.data.get("folder_id")
        folder = document.folder
        if folder_id:
            folder = Folder.objects.filter(is_deleted=False, id=folder_id).first()
        current = document.current_version_obj
        if not current or not current.file:
            return Response({"detail": "Nessun file da copiare."}, status=status.HTTP_400_BAD_REQUEST)
        new_doc = Document.objects.create(
            title=new_title,
            description=document.description,
            folder=folder,
            status=Document.STATUS_DRAFT,
            current_version=1,
            created_by=request.user,
        )
        new_version = DocumentVersion.objects.create(
            document=new_doc,
            version_number=1,
            file_name=current.file_name,
            file_size=current.file_size,
            file_type=current.file_type,
            checksum=current.checksum or "",
            created_by=request.user,
            is_current=True,
        )
        try:
            new_version.file.save(current.file_name, File(current.file.open("rb")), save=True)
        except (ValueError, OSError):
            new_doc.delete()
            return Response({"detail": "Errore copia file."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(
            DocumentDetailSerializer(new_doc, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["patch"], url_path="metadata")
    def update_metadata(self, request, pk=None):
        """Aggiorna solo metadata_values con validazione."""
        document = self.get_object()
        if document.locked_by_id and document.locked_by_id != request.user.id and getattr(request.user, "role", None) != "ADMIN":
            return Response({"detail": "Documento bloccato."}, status=status.HTTP_409_CONFLICT)
        can_write = document.user_permissions.filter(user=request.user, can_write=True).exists()
        if not can_write and document.created_by_id != request.user.id and getattr(request.user, "role", None) != "ADMIN":
            return Response({"detail": "Non autorizzato."}, status=status.HTTP_403_FORBIDDEN)
        values = request.data.get("metadata_values")
        if values is None:
            return Response({"metadata_values": "Obbligatorio."}, status=status.HTTP_400_BAD_REQUEST)
        if document.metadata_structure_id:
            from apps.metadata.validators import validate_metadata_values
            meta_errors = validate_metadata_values(document.metadata_structure, values)
            if meta_errors:
                return Response(
                    {"metadata_values": {e["field"]: e["message"] for e in meta_errors}},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        document.metadata_values = values
        document.save(update_fields=["metadata_values", "updated_at"])
        return Response(DocumentDetailSerializer(document, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="protocollo")
    def protocollo(self, request, pk=None):
        """Crea un protocollo in uscita collegato a questo documento (shortcut)."""
        document = self.get_object()
        if document.is_protocolled:
            return Response(
                {"detail": "Documento già protocollato."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from apps.protocols.models import Protocol, ProtocolCounter
        from apps.organizations.models import OrganizationalUnit
        from apps.protocols.views import _user_ou_ids
        from apps.protocols.serializers import ProtocolDetailSerializer

        ou_id = request.data.get("organizational_unit_id")
        if not ou_id:
            return Response(
                {"organizational_unit_id": "Obbligatorio."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ou = OrganizationalUnit.objects.filter(pk=ou_id).first()
        if not ou:
            return Response(
                {"organizational_unit_id": "UO non trovata."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ou_ids = _user_ou_ids(request.user)
        if getattr(request.user, "role", None) != "ADMIN" and ou.id not in ou_ids:
            return Response(
                {"detail": "Non autorizzato a creare protocolli per questa UO."},
                status=status.HTTP_403_FORBIDDEN,
            )
        subject = (request.data.get("subject") or document.title or "").strip()[:500]
        if not subject:
            return Response(
                {"subject": "Oggetto obbligatorio."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        year = timezone.now().year
        next_number = ProtocolCounter.get_next_number(ou, year)
        protocol_id = f"{year}/{ou.code}/{next_number:04d}"
        protocol = Protocol(
            number=next_number,
            year=year,
            organizational_unit=ou,
            protocol_id=protocol_id,
            direction="out",
            document=document,
            subject=subject,
            sender_receiver=(request.data.get("sender_receiver") or "").strip()[:500],
            registered_at=timezone.now(),
            registered_by=request.user,
            status="active",
            notes=(request.data.get("notes") or "").strip(),
            protocol_number=protocol_id,
            protocol_date=timezone.now(),
            created_by=request.user,
        )
        protocol.save()
        Document.objects.filter(pk=document.pk).update(
            is_protocolled=True, updated_at=timezone.now()
        )
        return Response(
            ProtocolDetailSerializer(protocol, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="start_workflow")
    def start_workflow(self, request, pk=None):
        """Avvia un workflow sul documento (RF-053). Solo ADMIN o can_write."""
        document = self.get_object()
        can_write = document.user_permissions.filter(user=request.user, can_write=True).exists()
        if not can_write and document.created_by_id != request.user.id and getattr(request.user, "role", None) != "ADMIN":
            return Response({"detail": "Non autorizzato."}, status=status.HTTP_403_FORBIDDEN)
        if document.workflow_instances.filter(status="active").exists():
            return Response(
                {"detail": "Documento ha già un workflow attivo."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        template_id = request.data.get("template_id")
        if not template_id:
            return Response({"template_id": "Obbligatorio."}, status=status.HTTP_400_BAD_REQUEST)
        from apps.workflows.models import WorkflowTemplate, WorkflowInstance, WorkflowStepInstance
        from apps.workflows.services import WorkflowService
        template = WorkflowTemplate.objects.filter(pk=template_id, is_published=True, is_deleted=False).first()
        if not template:
            return Response({"template_id": "Template non trovato o non pubblicato."}, status=status.HTTP_400_BAD_REQUEST)
        steps = list(template.steps.all().order_by("order"))
        if not steps:
            return Response({"detail": "Template senza step."}, status=status.HTTP_400_BAD_REQUEST)
        instance = WorkflowInstance.objects.create(
            template=template,
            document=document,
            started_by=request.user,
            status="active",
            current_step_order=steps[0].order,
        )
        now = timezone.now()
        for step in steps:
            assignees = WorkflowService.get_assignees(step, document)
            deadline = None
            if step.deadline_days:
                from datetime import timedelta
                deadline = now + timedelta(days=step.deadline_days)
            si = WorkflowStepInstance.objects.create(
                workflow_instance=instance,
                step=step,
                status="in_progress" if step.order == steps[0].order else "pending",
                started_at=now if step.order == steps[0].order else None,
                deadline=deadline,
            )
            si.assigned_to.set(assignees)
        document.status = Document.STATUS_IN_REVIEW
        document.save(update_fields=["status", "updated_at"])
        try:
            from apps.notifications.services import NotificationService
            current_si = instance.step_instances.get(step=steps[0])
            NotificationService.notify_workflow_assigned(current_si)
        except Exception:
            pass
        from apps.workflows.serializers import WorkflowInstanceSerializer
        return Response(
            WorkflowInstanceSerializer(instance, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="workflow_action")
    def workflow_action(self, request, pk=None):
        """Esegue azione sullo step corrente: approve, reject, request_changes (RF-053..RF-055)."""
        document = self.get_object()
        from apps.workflows.models import WorkflowInstance, WorkflowStepInstance
        instance = document.workflow_instances.filter(status="active").first()
        if not instance:
            return Response({"detail": "Nessun workflow attivo."}, status=status.HTTP_400_BAD_REQUEST)
        current_si = instance.get_current_step()
        if not current_si:
            return Response({"detail": "Nessuno step corrente."}, status=status.HTTP_400_BAD_REQUEST)
        if not current_si.assigned_to.filter(pk=request.user.pk).exists() and getattr(request.user, "role", None) != "ADMIN":
            return Response({"detail": "Non sei assegnato a questo step."}, status=status.HTTP_403_FORBIDDEN)
        action_name = request.data.get("action")
        comment = (request.data.get("comment") or "").strip()
        if action_name not in ("approve", "reject", "request_changes"):
            return Response({"action": "Valori ammessi: approve, reject, request_changes."}, status=status.HTTP_400_BAD_REQUEST)
        if action_name == "reject" and not comment:
            return Response({"comment": "Obbligatorio per rifiuto."}, status=status.HTTP_400_BAD_REQUEST)
        now = timezone.now()
        current_si.status = "completed" if action_name == "approve" else "rejected" if action_name == "reject" else "in_progress"
        current_si.completed_at = now if action_name in ("approve", "reject") else None
        current_si.completed_by = request.user if action_name in ("approve", "reject") else None
        current_si.action_taken = action_name
        current_si.comment = comment
        current_si.save(update_fields=["status", "completed_at", "completed_by", "action_taken", "comment"])
        if action_name == "reject":
            instance.status = "rejected"
            instance.completed_at = now
            instance.save(update_fields=["status", "completed_at"])
            document.status = Document.STATUS_REJECTED
            document.save(update_fields=["status", "updated_at"])
            try:
                from apps.notifications.services import NotificationService
                NotificationService.notify_workflow_rejected(instance, comment)
            except Exception:
                pass
            return Response({"detail": "Workflow rifiutato.", "workflow": {"status": "rejected"}})
        if action_name == "request_changes":
            try:
                from apps.notifications.services import NotificationService
                NotificationService.notify_changes_requested(instance, comment)
            except Exception:
                pass
            return Response({"detail": "Richiesta modifiche inviata."})
        if action_name == "approve":
            next_steps = instance.template.steps.filter(order__gt=instance.current_step_order).order_by("order")
            if not next_steps.exists():
                instance.status = "completed"
                instance.completed_at = now
                instance.save(update_fields=["status", "completed_at"])
                document.status = Document.STATUS_APPROVED
                document.save(update_fields=["status", "updated_at"])
                try:
                    from apps.notifications.services import NotificationService
                    NotificationService.notify_workflow_completed(instance)
                except Exception:
                    pass
                return Response({"detail": "Workflow completato. Documento approvato."})
            next_step = next_steps.first()
            instance.current_step_order = next_step.order
            instance.save(update_fields=["current_step_order"])
            from apps.workflows.services import WorkflowService
            next_si = instance.step_instances.get(step=next_step)
            next_si.status = "in_progress"
            next_si.started_at = now
            next_si.assigned_to.set(WorkflowService.get_assignees(next_step, document))
            next_si.save(update_fields=["status", "started_at"])
            try:
                from apps.notifications.services import NotificationService
                NotificationService.notify_workflow_assigned(next_si)
            except Exception:
                pass
            return Response({"detail": "Step completato. Prossimo step attivo."})
        return Response({"detail": "OK"})

    @action(detail=True, methods=["get"], url_path="workflow_history")
    def workflow_history(self, request, pk=None):
        """Storico istanze workflow del documento (RF-056)."""
        document = self.get_object()
        from apps.workflows.models import WorkflowInstance
        from apps.workflows.serializers import WorkflowInstanceSerializer
        instances = document.workflow_instances.all().order_by("-started_at")
        return Response(WorkflowInstanceSerializer(instances, many=True, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="request_signature")
    def request_signature(self, request, pk=None):
        """Avvia richiesta firma digitale (RF-075, RF-078). Documento deve essere APPROVED."""
        document = self.get_object()
        can_write = document.user_permissions.filter(user=request.user, can_write=True).exists()
        if not can_write and document.created_by_id != request.user.id and getattr(request.user, "role", None) != "ADMIN":
            return Response({"detail": "Non autorizzato."}, status=status.HTTP_403_FORBIDDEN)
        if document.status != Document.STATUS_APPROVED:
            return Response(
                {"detail": "Il documento deve essere in stato Approvato per richiedere la firma."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if document.metadata_structure_id and not getattr(document.metadata_structure, "signature_enabled", False):
            return Response(
                {"detail": "La struttura metadati di questo documento non consente la firma."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from apps.signatures.serializers import RequestSignatureSerializer
        from apps.signatures.services import SignatureService

        ser = RequestSignatureSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        signer_id = ser.validated_data["signer_id"]
        format_type = ser.validated_data.get("format")
        if format_type is None and document.metadata_structure_id:
            format_type = getattr(document.metadata_structure, "signature_format", "pades_invisible")
        format_type = format_type or "pades_invisible"
        reason = ser.validated_data.get("reason", "")
        location = ser.validated_data.get("location", "")

        User = get_user_model()
        signer = User.objects.filter(pk=signer_id).first()
        if not signer:
            return Response({"signer_id": "Utente non trovato."}, status=status.HTTP_400_BAD_REQUEST)
        if document.metadata_structure_id:
            allowed = document.metadata_structure.allowed_signers.all()
            if allowed.exists() and signer not in allowed:
                return Response(
                    {"detail": "L'utente selezionato non è un firmatario autorizzato per questo tipo di documento."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        version = getattr(document, "current_version_obj", None) or document.versions.filter(is_current=True).first()
        if not version:
            return Response({"detail": "Nessuna versione corrente del documento."}, status=status.HTTP_400_BAD_REQUEST)

        sig, otp_message = SignatureService.request(
            document=document,
            document_version=version,
            requested_by=request.user,
            signer=signer,
            format_type=format_type,
            reason=reason,
            location=location,
        )
        return Response(
            {"signature_request_id": str(sig.id), "otp_message": otp_message},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"], url_path="signatures")
    def signatures_list(self, request, pk=None):
        """Storico firme del documento (RF-075)."""
        document = self.get_object()
        from apps.signatures.serializers import SignatureRequestSerializer
        qs = document.signature_requests.all().order_by("-created_at")
        return Response(SignatureRequestSerializer(qs, many=True).data)

    @action(detail=True, methods=["post"], url_path="send_to_conservation")
    def send_to_conservation(self, request, pk=None):
        """Invia documento in conservazione (RF-079). Solo ADMIN o APPROVER. Doc APPROVED + almeno una firma."""
        document = self.get_object()
        if getattr(request.user, "role", None) not in ("ADMIN", "APPROVER"):
            return Response({"detail": "Solo ADMIN o APPROVER."}, status=status.HTTP_403_FORBIDDEN)
        if document.status != Document.STATUS_APPROVED:
            return Response(
                {"detail": "Il documento deve essere Approvato per l'invio in conservazione."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if document.metadata_structure_id and not getattr(document.metadata_structure, "conservation_enabled", False):
            return Response(
                {"detail": "La struttura metadati di questo documento non consente l'invio in conservazione."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not document.signature_requests.filter(status="completed").exists():
            return Response(
                {"detail": "È richiesta almeno una firma completata prima dell'invio in conservazione."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if document.conservation_requests.filter(status__in=["sent", "in_progress", "completed"]).exists():
            return Response(
                {"detail": "Esiste già una richiesta di conservazione per questo documento."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from apps.signatures.serializers import SendToConservationSerializer
        from apps.signatures.services import ConservationService

        ser = SendToConservationSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        version = getattr(document, "current_version_obj", None) or document.versions.filter(is_current=True).first()
        if not version:
            return Response({"detail": "Nessuna versione corrente."}, status=status.HTTP_400_BAD_REQUEST)

        doc_type = ser.validated_data.get("document_type") or (document.metadata_structure.conservation_document_type if document.metadata_structure_id else "") or "Documento"
        cons_class = ser.validated_data.get("conservation_class")
        if cons_class is None and document.metadata_structure_id:
            cons_class = getattr(document.metadata_structure, "conservation_class", "1")
        cons_class = cons_class or "1"
        metadata = {
            "document_type": doc_type,
            "document_date": ser.validated_data["document_date"],
            "reference_number": ser.validated_data.get("reference_number", ""),
            "conservation_class": cons_class,
        }
        protocol = document.protocols.first() if hasattr(document, "protocols") else None
        cons = ConservationService.submit(
            document=document,
            document_version=version,
            requested_by=request.user,
            metadata=metadata,
            protocol=protocol,
        )
        from apps.signatures.serializers import ConservationRequestSerializer
        return Response(
            {"conservation_request_id": str(cons.id), "status": cons.status},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"], url_path="conservation")
    def conservation_list(self, request, pk=None):
        """Stato conservazione del documento (RF-080)."""
        document = self.get_object()
        from apps.signatures.serializers import ConservationRequestSerializer
        qs = document.conservation_requests.all().order_by("-created_at")
        return Response(ConservationRequestSerializer(qs, many=True).data)

    @action(detail=True, methods=["post"], url_path="share")
    def share(self, request, pk=None):
        """Crea link di condivisione per il documento (FASE 11)."""
        document = self.get_object()
        from apps.sharing.serializers import ShareLinkCreateSerializer
        from apps.sharing.services import create_share_link
        from apps.sharing.serializers import ShareLinkSerializer
        from django.conf import settings

        ser = ShareLinkCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        recipient_user = None
        if data["recipient_type"] == "internal" and data.get("recipient_user_id"):
            recipient_user = User.objects.filter(pk=data["recipient_user_id"]).first()
            if not recipient_user:
                return Response({"recipient_user_id": "Utente non trovato."}, status=status.HTTP_400_BAD_REQUEST)

        share, err = create_share_link(
            request=request,
            target_type="document",
            document=document,
            recipient_type=data["recipient_type"],
            recipient_user=recipient_user,
            recipient_email=data.get("recipient_email", ""),
            recipient_name=data.get("recipient_name", ""),
            can_download=data.get("can_download", True),
            expires_in_days=data.get("expires_in_days"),
            max_accesses=data.get("max_accesses"),
            password=data.get("password"),
        )
        frontend = getattr(settings, "FRONTEND_URL", "") or ""
        url = f"{frontend}/share/{share.token}"
        return Response(
            {"share_link_id": str(share.id), "token": share.token, "url": url},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"], url_path="shares")
    def shares_list(self, request, pk=None):
        """Lista condivisioni attive del documento. Solo can_write, creatore o ADMIN."""
        document = self.get_object()
        can_write = document.user_permissions.filter(user=request.user, can_write=True).exists()
        is_creator = document.created_by_id == request.user.id
        if not can_write and not is_creator and getattr(request.user, "role", None) != "ADMIN":
            return Response({"detail": "Non autorizzato."}, status=status.HTTP_403_FORBIDDEN)
        from apps.sharing.serializers import ShareLinkSerializer
        qs = document.share_links.all().select_related("recipient_user", "shared_by").order_by("-created_at")
        return Response(ShareLinkSerializer(qs, many=True).data)

    @action(detail=True, methods=["post"], url_path="chat")
    def chat(self, request, pk=None):
        """Crea o recupera la chat per il documento (FASE 13)."""
        document = self.get_object()
        from apps.chat.models import ChatRoom, ChatMembership
        from apps.chat.serializers import ChatRoomSerializer
        room = ChatRoom.get_or_create_for_document(document)
        ChatMembership.objects.get_or_create(room=room, user=request.user)
        return Response(ChatRoomSerializer(room, context={"request": request}).data)

    @action(detail=True, methods=["patch"], url_path="move")
    def move(self, request, pk=None):
        document = self.get_object()
        folder_id = request.data.get("folder_id")
        folder = None
        if folder_id:
            folder = Folder.objects.filter(is_deleted=False, id=folder_id).first()
            if not folder:
                return Response({"folder_id": "Cartella non valida."}, status=status.HTTP_400_BAD_REQUEST)
        document.folder = folder
        document.save(update_fields=["folder"])
        return Response(DocumentListSerializer(document, context={"request": request}).data)

    @action(detail=True, methods=["get", "post"], url_path="attachments")
    def attachments(self, request, pk=None):
        document = self.get_object()
        if request.method == "GET":
            atts = document.attachments.all()
            data = DocumentAttachmentSerializer(atts, many=True).data
            for i, att in enumerate(atts):
                data[i]["download_url"] = f"/api/documents/{document.id}/attachments/{att.id}/download/"
            return Response(data)
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"file": "Obbligatorio."}, status=status.HTTP_400_BAD_REQUEST)
        att = DocumentAttachment.objects.create(
            document=document,
            file_name=file_obj.name or "allegato",
            file_size=file_obj.size,
            file_type=file_obj.content_type or "application/octet-stream",
            uploaded_by=request.user,
            description=(request.data.get("description") or "").strip()[:500],
        )
        att.file.save(file_obj.name or "file", file_obj, save=True)
        return Response(
            DocumentAttachmentSerializer(att).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["delete"], url_path=r"attachments/(?P<att_id>[^/.]+)")
    def attachment_delete(self, request, pk=None, att_id=None):
        document = self.get_object()
        att = document.attachments.filter(id=att_id).first()
        if not att:
            return Response(status=status.HTTP_404_NOT_FOUND)
        att.file.delete(save=False)
        att.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"], url_path=r"attachments/(?P<att_id>[^/.]+)/download")
    def attachment_download(self, request, pk=None, att_id=None):
        document = self.get_object()
        att = document.attachments.filter(id=att_id).first()
        if not att or not att.file:
            return Response(status=status.HTTP_404_NOT_FOUND)
        try:
            f = att.file.open("rb")
            return FileResponse(f, as_attachment=True, filename=att.file_name)
        except (ValueError, OSError):
            return Response(status=status.HTTP_404_NOT_FOUND)

    def get_permissions(self):
        if self.action in ("encrypt", "decrypt_download"):
            return [IsAuthenticated(), IsAdminRole()]
        return [IsAuthenticated(), CanAccessDocument()]

    @action(detail=True, methods=["post"], url_path="encrypt")
    def encrypt(self, request, pk=None):
        """
        POST /api/documents/{id}/encrypt/
        Body: { "password": "..." }
        """
        document = self.get_object()
        password = (request.data.get("password") or "").strip()
        if not password or len(password) < 8:
            return Response(
                {"password": "Password richiesta (min 8 caratteri)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        current = document.current_version_obj
        if not current or not current.file:
            return Response(
                {"detail": "Nessun file da cifrare."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            file_path = current.file.path
        except ValueError:
            return Response(
                {"detail": "File non disponibile su disco."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            encrypted_path, salt_b64 = DocumentEncryption.encrypt_file(file_path, password)
        except Exception as e:
            return Response(
                {"detail": f"Errore cifratura: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        agg = document.versions.aggregate(max_v=Max("version_number"))
        next_num = (agg.get("max_v") or 0) + 1
        new_version = DocumentVersion.objects.create(
            document=document,
            version_number=next_num,
            is_encrypted=True,
            encryption_salt=salt_b64,
        )
        with open(encrypted_path, "rb") as f:
            name = f"encrypted_v{next_num}.enc"
            new_version.file.save(name, File(f), save=True)
        document.versions.exclude(version_number=next_num).update(is_current=False)
        new_version.is_current = True
        new_version.save(update_fields=["is_current"])
        document.current_version = next_num
        document.save(update_fields=["current_version"])
        import os
        try:
            os.remove(encrypted_path)
        except OSError:
            pass
        AuditLog.log(request.user, "DOCUMENT_ENCRYPTED", {"document_id": str(document.id), "version": next_num}, request)
        return Response({
            "message": "Documento cifrato. Versione %s creata." % next_num,
            "new_version": next_num,
            "warning": "Conserva la password in un luogo sicuro. Non è recuperabile.",
        })

    @action(detail=True, methods=["post"], url_path="decrypt_download")
    def decrypt_download(self, request, pk=None):
        """
        POST /api/documents/{id}/decrypt_download/
        Body: { "password": "..." }
        """
        from cryptography.exceptions import InvalidTag
        document = self.get_object()
        password = (request.data.get("password") or "").strip()
        current = document.current_version_obj
        if not current or not current.is_encrypted or not current.file:
            return Response(
                {"detail": "Documento non cifrato o file assente."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            file_path = current.file.path
        except ValueError:
            return Response(
                {"detail": "File non disponibile."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            plaintext = DocumentEncryption.decrypt_file(file_path, password)
        except InvalidTag:
            return Response(
                {"detail": "Password non corretta."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"detail": f"Errore decifratura: {e}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        AuditLog.log(request.user, "DOCUMENT_DOWNLOADED", {"document_id": str(document.id), "decrypted": True}, request)
        base_name = document.title or "document"
        if base_name.lower().endswith(".enc"):
            base_name = base_name[:-4]
        response = FileResponse(ContentFile(plaintext), as_attachment=True, filename=base_name)
        return response
