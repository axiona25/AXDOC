from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import DocumentTemplateViewSet

router = DefaultRouter()
router.register(r"", DocumentTemplateViewSet, basename="document-template")

urlpatterns = [path("", include(router.urls))]
