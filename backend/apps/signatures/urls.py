from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    ConservationRequestViewSet,
    ExtractP7MView,
    SignatureRequestViewSet,
    VerifyP7MView,
)

router = DefaultRouter()
router.register(r"signatures", SignatureRequestViewSet, basename="signature-request")
router.register(r"conservation", ConservationRequestViewSet, basename="conservation-request")

urlpatterns = [
    path("verify_p7m/", VerifyP7MView.as_view(), name="verify-p7m"),
    path("extract_p7m/", ExtractP7MView.as_view(), name="extract-p7m"),
] + router.urls
