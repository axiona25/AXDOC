from rest_framework.routers import SimpleRouter

from .security_views import SecurityIncidentViewSet

router = SimpleRouter()
router.register(r"security-incidents", SecurityIncidentViewSet, basename="security-incident")

urlpatterns = router.urls
