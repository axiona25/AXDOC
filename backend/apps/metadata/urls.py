from rest_framework.routers import DefaultRouter
from .views import MetadataStructureViewSet

router = DefaultRouter()
router.register(r"structures", MetadataStructureViewSet, basename="metadatastructure")
urlpatterns = router.urls
