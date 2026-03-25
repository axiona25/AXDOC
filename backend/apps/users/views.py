"""
ViewSet utenti (RF-011..RF-020) e import massivo (RF-017).
"""
import hashlib
import json

from django.db import models
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound, PermissionDenied
from drf_spectacular.utils import extend_schema, extend_schema_view

from django.contrib.auth import get_user_model

from .models import User, UserGroup, UserGroupMembership, ConsentRecord, CONSENT_TYPE_CHOICES
from .serializers import (
    UserSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
    UserProfileSerializer,
    UserCreateManualSerializer,
    UserGroupSerializer,
    UserGroupDetailSerializer,
    UserGroupMembershipSerializer,
    ConsentRecordSerializer,
)
from .permissions import IsAdminOrSelf, IsAdminRole
from .guest_permissions import IsInternalUser
from .importers import UserImporter
from apps.organizations.mixins import TenantFilterMixin

User = get_user_model()


@extend_schema_view(
    list=extend_schema(tags=["Utenti"], summary="Lista utenti"),
    create=extend_schema(tags=["Utenti"], summary="Crea utente"),
    retrieve=extend_schema(tags=["Utenti"], summary="Dettaglio utente"),
    update=extend_schema(tags=["Utenti"], summary="Aggiorna utente"),
    partial_update=extend_schema(tags=["Utenti"], summary="Aggiorna parziale utente"),
    destroy=extend_schema(tags=["Utenti"], summary="Elimina utente"),
)
class UserViewSet(TenantFilterMixin, viewsets.ModelViewSet):
    """
    CRUD utenti.
    list, create, destroy: solo ADMIN.
    retrieve, update: ADMIN oppure utente stesso.
    """

    queryset = User.objects.filter(is_deleted=False)
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "list" or self.action == "retrieve":
            return UserSerializer
        if self.action == "create":
            return UserCreateSerializer
        if self.action in ("update", "partial_update"):
            if "pk" in self.kwargs:
                try:
                    obj = self.get_object()
                    if obj == self.request.user and self.request.user.role != "ADMIN":
                        return UserProfileSerializer
                except (NotFound, PermissionDenied):
                    pass
            return UserUpdateSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action in ("my_consents", "export_my_data"):
            return [IsAuthenticated()]
        if self.action == "anonymize":
            return [IsAuthenticated(), IsAdminRole(), IsInternalUser()]
        if self.action in (
            "list",
            "create",
            "destroy",
            "deactivate",
            "reactivate",
            "import_template",
            "import_preview",
            "import_users",
            "create_manual",
            "change_type",
            "reset_password",
            "get_permissions_detail",
            "set_permission",
        ):
            return [IsAuthenticated(), IsAdminRole(), IsInternalUser()]
        return [IsAuthenticated(), IsAdminOrSelf()]

    def update(self, request, *args, **kwargs):
        """Esegue update con UserUpdateSerializer ma ritorna la risposta con UserSerializer (include organizational_unit)."""
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        if getattr(instance, "_prefetched_objects_cache", None):
            instance._prefetched_objects_cache = {}
        # Ricarica l'istanza dal DB per avere organizational_unit aggiornata
        instance.refresh_from_db()
        return Response(UserSerializer(instance, context={"request": request}).data)

    def get_queryset(self):
        qs = super().get_queryset()
        role = self.request.query_params.get("role")
        if role:
            qs = qs.filter(role=role)
        user_type = self.request.query_params.get("user_type")
        if user_type in ("internal", "guest"):
            qs = qs.filter(user_type=user_type)
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(
                models.Q(first_name__icontains=search)
                | models.Q(last_name__icontains=search)
                | models.Q(email__icontains=search)
            )
        ou_id = self.request.query_params.get("ou")
        if ou_id:
            from apps.organizations.models import OrganizationalUnitMembership
            user_ids = OrganizationalUnitMembership.objects.filter(
                organizational_unit_id=ou_id, is_active=True
            ).values_list("user_id", flat=True)
            qs = qs.filter(pk__in=user_ids)

        unassigned = self.request.query_params.get("unassigned")
        if unassigned and unassigned.lower() == "true":
            from apps.organizations.models import OrganizationalUnitMembership
            assigned_ids = OrganizationalUnitMembership.objects.filter(
                is_active=True
            ).values_list("user_id", flat=True)
            qs = qs.exclude(pk__in=assigned_ids)
        return qs.order_by("-date_joined")

    def destroy(self, request, *args, **kwargs):
        """Soft delete: modifica email per liberarla e imposta is_deleted=True."""
        instance = self.get_object()
        # Libera l'email aggiungendo suffisso deleted+timestamp
        import time
        instance.email = f"{instance.email}.deleted_{int(time.time())}"
        instance.is_deleted = True
        instance.is_active = False
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"])
    def me(self, request):
        """GET /api/users/me/ — profilo utente loggato."""
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=["get", "post"], url_path="my_consents")
    def my_consents(self, request):
        """GET/POST /api/users/my_consents/ — consensi GDPR correnti o nuovo record."""
        if request.method == "GET":
            latest = []
            for value, _label in CONSENT_TYPE_CHOICES:
                row = (
                    ConsentRecord.objects.filter(user=request.user, consent_type=value)
                    .order_by("-created_at")
                    .first()
                )
                if row:
                    latest.append(row)
            return Response(ConsentRecordSerializer(latest, many=True).data)

        serializer = ConsentRecordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        ip = (
            x_forwarded.split(",")[0].strip()
            if x_forwarded
            else request.META.get("REMOTE_ADDR")
        )
        record = serializer.save(
            user=request.user,
            ip_address=ip or None,
            user_agent=request.META.get("HTTP_USER_AGENT", "") or "",
        )
        if record.consent_type == "privacy_policy" and record.granted:
            User.objects.filter(pk=request.user.pk).update(
                privacy_accepted_at=timezone.now()
            )
        return Response(ConsentRecordSerializer(record).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="export_my_data")
    def export_my_data(self, request):
        """GET /api/users/export_my_data/ — portabilità GDPR (JSON)."""
        from apps.authentication.models import AuditLog
        from apps.documents.models import Document

        user = request.user
        data = {
            "personal_info": {
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone": getattr(user, "phone", "") or "",
                "role": user.role,
                "user_type": getattr(user, "user_type", "") or "",
                "date_joined": user.date_joined.isoformat() if user.date_joined else None,
            },
            "consents": list(
                ConsentRecord.objects.filter(user=user).values(
                    "consent_type", "version", "granted", "created_at"
                )
            ),
            "documents_created": list(
                Document.objects.filter(created_by=user, is_deleted=False).values(
                    "id", "title", "status", "created_at"
                )[:1000]
            ),
            "audit_log": list(
                AuditLog.objects.filter(user=user).values(
                    "action", "detail", "timestamp"
                ).order_by("-timestamp")[:500]
            ),
            "exported_at": timezone.now().isoformat(),
        }
        response = HttpResponse(
            json.dumps(data, default=str, indent=2),
            content_type="application/json; charset=utf-8",
        )
        response["Content-Disposition"] = (
            f'attachment; filename="axdoc_my_data_{user.id}.json"'
        )
        return response

    @action(detail=True, methods=["post"], url_path="anonymize")
    def anonymize(self, request, pk=None):
        """POST /api/users/{id}/anonymize/ — diritto all'oblio (solo ADMIN)."""
        from apps.authentication.models import AuditLog

        if request.user.role != "ADMIN":
            return Response({"detail": "Solo ADMIN."}, status=status.HTTP_403_FORBIDDEN)
        target = self.get_object()
        if target == request.user:
            return Response(
                {"detail": "Non puoi anonimizzare te stesso."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        anon_hash = hashlib.sha256(str(target.id).encode()).hexdigest()[:12]
        target.email = f"anonymized_{anon_hash}@deleted.local"
        target.first_name = "Utente"
        target.last_name = "Anonimizzato"
        target.phone = ""
        target.is_active = False
        target.is_deleted = True
        target.save()
        ConsentRecord.objects.filter(user=target).delete()
        AuditLog.log(
            request.user,
            "USER_ANONYMIZED",
            {"anonymized_user_id": str(target.id)},
            request,
        )
        return Response({"detail": "Utente anonimizzato."})

    @action(detail=False, methods=["post"], url_path="create_manual")
    def create_manual(self, request):
        """
        POST /api/users/create_manual/ — crea utente senza invito email.
        Body: email, first_name, last_name, user_type (internal|guest), role (opz, per internal),
        organizational_unit_id (opz), password (opz, se vuoto generata), send_welcome_email (default true).
        Solo ADMIN, solo utenti interni.
        """
        import secrets
        import string
        
        # Genera password se non fornita dall'utente
        provided_password = (request.data.get("password") or "").strip()
        provided_by_user = bool(provided_password)
        
        if not provided_by_user:
            alphabet = string.ascii_letters + string.digits
            generated_password = "".join(secrets.choice(alphabet) for _ in range(16))
        else:
            generated_password = provided_password
        
        # Prepara i dati per il serializer
        serializer_data = request.data.copy()
        if not provided_by_user:
            serializer_data["password"] = generated_password
        
        serializer = UserCreateManualSerializer(data=serializer_data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        send_welcome_email = serializer.validated_data.get("send_welcome_email", True)
        
        return Response({
            "user": UserSerializer(user).data,
            "generated_password": generated_password if not provided_by_user else None,
            "welcome_email_sent": send_welcome_email,
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="change_type")
    def change_type(self, request, pk=None):
        """
        POST /api/users/{id}/change_type/ — cambia user_type (internal/guest).
        Body: { "user_type": "internal" | "guest" }. Solo ADMIN.
        """
        user = self.get_object()
        new_type = (request.data.get("user_type") or "").strip().lower()
        if new_type not in ("internal", "guest"):
            return Response(
                {"user_type": "Valore non valido. Usare internal o guest."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.user_type = new_type
        if new_type == "guest":
            user.role = "OPERATOR"
        user.save(update_fields=["user_type", "role", "updated_at"])
        return Response(UserSerializer(user).data)

    @action(detail=True, methods=["post"], url_path="reset_password")
    def reset_password(self, request, pk=None):
        """
        POST /api/users/<id>/reset_password/
        Genera nuova password temporanea per l'utente. Solo ADMIN.
        """
        if request.user.role != "ADMIN":
            return Response({"detail": "Non autorizzato."}, status=status.HTTP_403_FORBIDDEN)
        
        import secrets
        import string
        instance = self.get_object()
        alphabet = string.ascii_letters + string.digits
        new_password = "".join(secrets.choice(alphabet) for _ in range(16))
        instance.set_password(new_password)
        instance.must_change_password = True
        instance.save(update_fields=["password", "must_change_password", "updated_at"])
        return Response({
            "detail": "Password reimpostata con successo.",
            "generated_password": new_password,
        })

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsAdminRole])
    def deactivate(self, request, pk=None):
        """Disattiva utente (solo ADMIN)."""
        user = self.get_object()
        user.is_active = False
        user.save(update_fields=["is_active", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsAdminRole])
    def reactivate(self, request, pk=None):
        """Riattiva utente (solo ADMIN)."""
        user = self.get_object()
        user.is_active = True
        user.save(update_fields=["is_active", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    # --- Import utenti (RF-017) ---
    def _get_import_permissions(self):
        return [IsAuthenticated(), IsAdminRole()]

    @action(detail=False, methods=["get"], url_path="import/template")
    def import_template(self, request):
        """GET /api/users/import/template/?format=csv|xlsx — scarica template."""
        self.permission_classes = [IsAdminRole]
        self.check_permissions(request)
        fmt = (request.query_params.get("file_format") or "csv").lower()
        if fmt not in ("csv", "xlsx"):
            return Response(
                {"detail": "format deve essere csv o xlsx"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        importer = UserImporter()
        if fmt == "csv":
            content = importer.get_template_csv()
            response = HttpResponse(content, content_type="text/csv; charset=utf-8")
            response["Content-Disposition"] = 'attachment; filename="template_utenti.csv"'
            return response
        content = importer.get_template_xlsx()
        response = HttpResponse(content, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = 'attachment; filename="template_utenti.xlsx"'
        return response

    @action(detail=False, methods=["post"], url_path="import/preview")
    def import_preview(self, request):
        """POST /api/users/import/preview/ — valida file senza creare utenti."""
        self.permission_classes = [IsAdminRole]
        self.check_permissions(request)
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response(
                {"detail": "File mancante."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        name = (file_obj.name or "").lower()
        if name.endswith(".xlsx"):
            file_type = "xlsx"
        elif name.endswith(".csv"):
            file_type = "csv"
        else:
            return Response(
                {"detail": "Formato non supportato. Usa .csv o .xlsx"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        importer = UserImporter()
        try:
            rows = importer.parse_file(file_obj, file_type)
        except Exception as e:
            return Response(
                {"detail": f"Errore lettura file: {e}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        preview = []
        valid_count = 0
        for i, row in enumerate(rows):
            row_num = i + 1
            errors = importer.validate_row(row, row_num)
            valid = len(errors) == 0
            if valid:
                valid_count += 1
            preview.append({
                "row": row_num,
                "email": row.get("email", ""),
                "name": f"{row.get('first_name', '')} {row.get('last_name', '')}".strip(),
                "valid": valid,
                "errors": errors,
            })
        return Response({
            "total_rows": len(rows),
            "valid_rows": valid_count,
            "invalid_rows": len(rows) - valid_count,
            "preview": preview,
        })

    @action(detail=False, methods=["post"], url_path="import")
    def import_users(self, request):
        """POST /api/users/import/ — importa utenti da file (send_invite in body o form)."""
        self.permission_classes = [IsAdminRole]
        self.check_permissions(request)
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response(
                {"detail": "File mancante."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        send_invite = request.data.get("send_invite", True)
        if isinstance(send_invite, str):
            send_invite = send_invite.lower() in ("true", "1", "yes")
        name = (file_obj.name or "").lower()
        if name.endswith(".xlsx"):
            file_type = "xlsx"
        elif name.endswith(".csv"):
            file_type = "csv"
        else:
            return Response(
                {"detail": "Formato non supportato. Usa .csv o .xlsx"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        importer = UserImporter()
        try:
            rows = importer.parse_file(file_obj, file_type)
        except Exception as e:
            return Response(
                {"detail": f"Errore lettura file: {e}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        report = importer.import_users(rows, send_invite=send_invite, created_by=request.user)
        from apps.authentication.models import AuditLog
        AuditLog.log(
            request.user,
            "USERS_IMPORTED",
            {"report": report, "send_invite": send_invite},
            request,
        )
        return Response(report)

    @action(detail=True, methods=["get"], url_path="permissions")
    def get_permissions_detail(self, request, pk=None):
        """GET /api/users/{id}/permissions/ — lista permessi espliciti dell'utente su documenti e fascicoli."""
        user = self.get_object()
        from apps.documents.models import DocumentPermission
        from apps.dossiers.models import DossierPermission

        doc_perms = DocumentPermission.objects.filter(user=user).select_related("document")
        dossier_perms = DossierPermission.objects.filter(user=user).select_related("dossier")

        return Response({
            "documents": [
                {
                    "document_id": str(dp.document_id),
                    "document_title": dp.document.title if dp.document else "",
                    "can_read": dp.can_read,
                    "can_write": dp.can_write,
                    "can_delete": dp.can_delete,
                }
                for dp in doc_perms
            ],
            "dossiers": [
                {
                    "dossier_id": str(dp.dossier_id),
                    "dossier_title": dp.dossier.title if dp.dossier else "",
                    "dossier_identifier": dp.dossier.identifier if dp.dossier else "",
                    "can_read": dp.can_read,
                    "can_write": dp.can_write,
                }
                for dp in dossier_perms
            ],
        })

    @action(detail=True, methods=["post"], url_path="set_permission")
    def set_permission(self, request, pk=None):
        """
        POST /api/users/{id}/set_permission/
        Body: { "type": "document"|"dossier", "target_id": "uuid", "can_read": true, "can_write": false, "can_delete": false }
        Per rimuovere: { "type": "document", "target_id": "uuid", "remove": true }
        """
        user = self.get_object()
        perm_type = request.data.get("type")
        target_id = request.data.get("target_id")
        remove = request.data.get("remove", False)

        if not perm_type or not target_id:
            return Response({"detail": "type e target_id obbligatori."}, status=status.HTTP_400_BAD_REQUEST)

        if perm_type == "document":
            from apps.documents.models import Document, DocumentPermission
            doc = Document.objects.filter(pk=target_id, is_deleted=False).first()
            if not doc:
                return Response({"detail": "Documento non trovato."}, status=status.HTTP_400_BAD_REQUEST)
            if remove:
                DocumentPermission.objects.filter(document=doc, user=user).delete()
                return Response({"removed": True})
            existing = DocumentPermission.objects.filter(document=doc, user=user).first()
            defaults = {
                "can_read": request.data.get("can_read", True),
                "can_write": request.data.get("can_write", False),
                "can_delete": (
                    request.data["can_delete"]
                    if "can_delete" in request.data
                    else (existing.can_delete if existing else False)
                ),
            }
            perm, _ = DocumentPermission.objects.update_or_create(
                document=doc,
                user=user,
                defaults=defaults,
            )
            return Response({
                "set": True,
                "can_read": perm.can_read,
                "can_write": perm.can_write,
                "can_delete": perm.can_delete,
            })

        if perm_type == "dossier":
            from apps.dossiers.models import Dossier, DossierPermission
            dossier = Dossier.objects.filter(pk=target_id, is_deleted=False).first()
            if not dossier:
                return Response({"detail": "Fascicolo non trovato."}, status=status.HTTP_400_BAD_REQUEST)
            if remove:
                DossierPermission.objects.filter(dossier=dossier, user=user).delete()
                return Response({"removed": True})
            perm, _ = DossierPermission.objects.update_or_create(
                dossier=dossier,
                user=user,
                defaults={
                    "can_read": request.data.get("can_read", True),
                    "can_write": request.data.get("can_write", False),
                },
            )
            return Response({"set": True, "can_read": perm.can_read, "can_write": perm.can_write})

        return Response({"detail": "type deve essere document o dossier."}, status=status.HTTP_400_BAD_REQUEST)


class UserGroupViewSet(TenantFilterMixin, viewsets.ModelViewSet):
    """
    CRUD gruppi utenti (RF-016).
    list, create, update, destroy: solo ADMIN.
    """
    queryset = UserGroup.objects.filter(is_active=True)
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return UserGroupDetailSerializer
        return UserGroupSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(models.Q(name__icontains=search) | models.Q(description__icontains=search))
        ou_id = self.request.query_params.get("ou")
        if ou_id:
            qs = qs.filter(organizational_unit_id=ou_id)
        return qs.order_by("name")

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])

    def get_perform_create_kwargs(self, serializer):
        return {"created_by": self.request.user}

    @action(detail=True, methods=["post"], url_path="add_members")
    def add_members(self, request, pk=None):
        """POST /api/groups/{id}/add_members/ — body: { "user_ids": ["uuid", ...] }"""
        group = self.get_object()
        user_ids = request.data.get("user_ids") or []
        if not isinstance(user_ids, list):
            return Response({"detail": "user_ids deve essere una lista."}, status=status.HTTP_400_BAD_REQUEST)
        added = 0
        for uid in user_ids:
            try:
                user = User.objects.get(pk=uid, is_deleted=False)
                _, created = UserGroupMembership.objects.get_or_create(
                    group=group,
                    user=user,
                    defaults={"added_by": request.user},
                )
                if created:
                    added += 1
            except User.DoesNotExist:
                continue
        return Response({"added": added})

    @action(detail=True, methods=["delete"], url_path="remove_member/(?P<user_id>[^/.]+)")
    def remove_member(self, request, pk=None, user_id=None):
        """DELETE /api/groups/{id}/remove_member/{user_id}/"""
        group = self.get_object()
        deleted, _ = UserGroupMembership.objects.filter(group=group, user_id=user_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT if deleted else status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=["get"], url_path="members")
    def members(self, request, pk=None):
        """GET /api/groups/{id}/members/ — lista membri."""
        group = self.get_object()
        members = group.memberships.select_related("user").all()
        serializer = UserGroupMembershipSerializer(members, many=True)
        return Response(serializer.data)
