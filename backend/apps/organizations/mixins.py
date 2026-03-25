"""
Mixin ViewSet: filtro queryset per tenant; superuser vede cross-tenant.
"""
from django.db.models import Q


class TenantFilterMixin:
    def filter_queryset_by_tenant(self, qs):
        if getattr(self.request.user, "is_superuser", False):
            return qs
        tenant = getattr(self.request, "tenant", None)
        if tenant and hasattr(qs.model, "tenant"):
            # Tenant "default": include record legacy senza tenant (transizione verso NOT NULL).
            if getattr(tenant, "slug", None) == "default":
                return qs.filter(Q(tenant=tenant) | Q(tenant__isnull=True))
            return qs.filter(tenant=tenant)
        return qs

    def get_queryset(self):
        qs = super().get_queryset()
        return self.filter_queryset_by_tenant(qs)

    def get_tenant_save_kwargs(self, serializer):
        if getattr(self.request.user, "is_superuser", False):
            return {}
        tenant = getattr(self.request, "tenant", None)
        model = serializer.Meta.model
        if tenant and hasattr(model, "tenant"):
            return {"tenant": tenant}
        return {}

    def get_perform_create_kwargs(self, serializer):
        """Override in sottoclassi per passare created_by, ecc."""
        return {}

    def perform_create(self, serializer):
        kw = {**self.get_tenant_save_kwargs(serializer), **self.get_perform_create_kwargs(serializer)}
        serializer.save(**kw)
