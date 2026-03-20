from rest_framework.routers import DefaultRouter

from .views import MailAccountViewSet, MailMessageViewSet

router = DefaultRouter()
router.register(r"accounts", MailAccountViewSet, basename="mail-account")
router.register(r"messages", MailMessageViewSet, basename="mail-message")
urlpatterns = router.urls
