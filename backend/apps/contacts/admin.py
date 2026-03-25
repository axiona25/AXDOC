from django.contrib import admin

from .models import Contact


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ["display_name", "email", "pec", "phone", "contact_type", "source"]
    search_fields = ["first_name", "last_name", "company_name", "email", "pec"]
    list_filter = ["contact_type", "source", "is_shared"]
