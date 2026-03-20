"""
ViewSet utenti (RF-011..RF-020) e import massivo (RF-017).
"""
from django.db import models
from django.http import HttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound, PermissionDenied

from django.contrib.auth import get_user_model

from .models import User, UserGroup, UserGroupMembership
from .serializers import (
    UserSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
    UserProfileSerializer,
    UserCreateManualSerializer,
    UserGroupSerializer,
    UserGroupDetailSerializer,
    UserGroupMembershipSerializer,
)
from .permissions import IsAdminOrSelf, IsAdminRole
from .guest_permissions import IsInternalUser
from .importers import UserImporter

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
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
        if self.action in ("list", "create", "destroy", "deactivate", "reactivate", "import_template", "import_preview", "import_users", "create_manual", "change_type"):
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

    def perform_destroy(self, instance):
        """Soft delete: is_deleted=True."""
        instance.is_deleted = True
        instance.is_active = False
        instance.save(update_fields=["is_deleted", "is_active", "updated_at"])

    @action(detail=False, methods=["get"])
    def me(self, request):
        """GET /api/users/me/ — profilo utente loggato."""
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="create_manual")
    def create_manual(self, request):
        """
        POST /api/users/create_manual/ — crea utente senza invito email.
        Body: email, first_name, last_name, user_type (internal|guest), role (opz, per internal),
        organizational_unit_id (opz), password (opz, se vuoto generata), send_welcome_email (default true).
        Solo ADMIN, solo utenti interni.
        """
        serializer = UserCreateManualSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            UserSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )

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


class UserGroupViewSet(viewsets.ModelViewSet):
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
        return qs.order_by("name")

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

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
