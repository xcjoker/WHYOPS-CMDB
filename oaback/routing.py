from django.urls import path
from apps.webssh import consumers

websocket_urlpatterns = [
    path('ssh_web/', consumers.TerminalConsumer.as_asgi()),
]