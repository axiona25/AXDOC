from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import OrganizationalUnitViewSet

router = DefaultRouter()
router.register(r"", OrganizationalUnitViewSet, basename="organizationalunit")
urlpatterns = [path("", include(router.urls))]
