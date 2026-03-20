from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DocumentArchiveViewSet,
    InformationPackageViewSet,
    RetentionRuleViewSet,
    TitolarioTreeView,
    TitolarioDetailView,
)

router = DefaultRouter()
router.register(r"documents", DocumentArchiveViewSet, basename="archive-document")
router.register(r"packages", InformationPackageViewSet, basename="archive-package")
router.register(r"retention-rules", RetentionRuleViewSet, basename="retention-rule")

urlpatterns = [
    path("", include(router.urls)),
    path("titolario/", TitolarioTreeView.as_view()),
    path("titolario/<str:code>/", TitolarioDetailView.as_view()),
]
