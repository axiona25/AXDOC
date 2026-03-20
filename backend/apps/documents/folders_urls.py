from rest_framework.routers import DefaultRouter
from .folder_views import FolderViewSet

router = DefaultRouter()
router.register(r"", FolderViewSet, basename="folder")
urlpatterns = router.urls
