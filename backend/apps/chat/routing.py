from django.urls import re_path
from .consumers import ChatConsumer, PresenceConsumer
from .call_consumer import CallConsumer

websocket_urlpatterns = [
    re_path(r"ws/chat/(?P<room_id>[0-9a-f-]+)/$", ChatConsumer.as_asgi()),
    re_path(r"ws/presence/$", PresenceConsumer.as_asgi()),
    re_path(r"ws/call/(?P<call_id>[0-9a-f-]+)/$", CallConsumer.as_asgi()),
]
