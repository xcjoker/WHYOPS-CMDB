import os
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application
import oaback.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oaback.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AllowedHostsOriginValidator(
        URLRouter(
            oaback.routing.websocket_urlpatterns
        )
    ),
})
