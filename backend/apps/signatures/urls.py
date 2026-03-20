from rest_framework.routers import DefaultRouter
from .views import SignatureRequestViewSet, ConservationRequestViewSet

router = DefaultRouter()
router.register(r"signatures", SignatureRequestViewSet, basename="signature-request")
router.register(r"conservation", ConservationRequestViewSet, basename="conservation-request")
urlpatterns = router.urls
