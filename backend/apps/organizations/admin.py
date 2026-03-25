from django.contrib import admin
from .models import Tenant, OrganizationalUnit, OrganizationalUnitMembership


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "plan", "is_active", "created_at"]
    list_filter = ["is_active", "plan"]
    search_fields = ["name", "slug", "domain"]


class OrganizationalUnitMembershipInline(admin.TabularInline):
    model = OrganizationalUnitMembership
    extra = 0


@admin.register(OrganizationalUnit)
class OrganizationalUnitAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "parent", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["code", "name"]
    inlines = [OrganizationalUnitMembershipInline]


@admin.register(OrganizationalUnitMembership)
class OrganizationalUnitMembershipAdmin(admin.ModelAdmin):
    list_display = ["user", "organizational_unit", "role", "is_active", "joined_at"]
    list_filter = ["role", "is_active"]
