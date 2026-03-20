from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserGroupViewSet

router = DefaultRouter()
router.register(r"", UserGroupViewSet, basename="group")
urlpatterns = [path("", include(router.urls))]
