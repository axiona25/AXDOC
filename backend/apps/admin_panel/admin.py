from django.contrib import admin
from .models import SystemLicense, SystemSettings


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    list_display = ["id", "updated_at"]
    readonly_fields = ["id", "updated_at"]


# SystemLicense may be registered elsewhere or in main app
if not admin.site.is_registered(SystemLicense):
    admin.site.register(SystemLicense)
