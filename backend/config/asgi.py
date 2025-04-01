import os

import django
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application
from django.urls import path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.shuttle.consumers.receiver import ReceiverConsumer  # v1 consumer  #noqa
from apps.shuttle.demultiplexer import Demultiplexer  # v2 consumer  #noqa
from apps.shuttle.utils.jwt_auth import JWTAuthMiddlewareStack  # noqa

websocket_urlpatterns = [
    # v1 endpoint: no custom token middleware
    path("api/ws/", ReceiverConsumer.as_asgi()),  # pyright: ignore
    # v2 endpoint: wrapped with token middlewares
    path("api/ws/v2/", JWTAuthMiddlewareStack(Demultiplexer.as_asgi())),  # pyright: ignore
]

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": AllowedHostsOriginValidator(URLRouter(websocket_urlpatterns)),
    }
)
