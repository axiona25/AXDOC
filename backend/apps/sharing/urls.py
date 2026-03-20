"""
URL Condivisione (FASE 11).
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ShareLinkViewSet

router = DefaultRouter()
router.register(r"", ShareLinkViewSet, basename="sharelink")

urlpatterns = [
    path("", include(router.urls)),
]
