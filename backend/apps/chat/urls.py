from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ChatRoomViewSet, ChatMessageViewSet, CallInitiateView, CallEndView, IceServersView

router = DefaultRouter()
router.register(r"rooms", ChatRoomViewSet, basename="chatroom")
router.register(r"messages", ChatMessageViewSet, basename="chatmessage")

urlpatterns = [
    path("", include(router.urls)),
    path("calls/initiate/", CallInitiateView.as_view()),
    path("calls/<uuid:call_id>/end/", CallEndView.as_view()),
    path("ice_servers/", IceServersView.as_view()),
]
