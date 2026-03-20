from django.urls import path
from .views import AuditLogViewSet, DocumentActivityView

urlpatterns = [
    path("", AuditLogViewSet.as_view(), name="audit-list"),
    path("document/<uuid:doc_id>/", DocumentActivityView.as_view(), name="audit-document"),
]
