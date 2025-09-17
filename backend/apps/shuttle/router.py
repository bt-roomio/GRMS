from channels.routing import URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.urls import path

from shuttle.consumers.receiver import ReceiverConsumer
from shuttle.demultiplexer import Demultiplexer
from shuttle.utils.jwt_auth import JWTAuthMiddlewareStack

websocket_urlpatterns = AllowedHostsOriginValidator(
    URLRouter(
        [
            # v1 endpoint: no custom token middleware
            path("api/ws/", ReceiverConsumer.as_asgi()),  # pyright: ignore
            # v2 endpoint: wrapped with token middlewares
            path("api/ws/v2/", JWTAuthMiddlewareStack(Demultiplexer.as_asgi())),  # pyright: ignore
        ]
    )
)
