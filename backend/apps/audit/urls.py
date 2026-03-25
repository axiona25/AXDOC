from django.urls import path
from .views import (
    AuditLogViewSet,
    AuditExportExcelView,
    AuditExportPdfView,
    DocumentActivityView,
)

urlpatterns = [
    path("", AuditLogViewSet.as_view(), name="audit-list"),
    path("export_excel/", AuditExportExcelView.as_view(), name="audit-export-excel"),
    path("export_pdf/", AuditExportPdfView.as_view(), name="audit-export-pdf"),
    path("document/<uuid:doc_id>/", DocumentActivityView.as_view(), name="audit-document"),
]
