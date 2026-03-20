from rest_framework.routers import DefaultRouter
from .views import ProtocolViewSet

router = DefaultRouter()
router.register(r"", ProtocolViewSet, basename="protocol")
urlpatterns = router.urls
