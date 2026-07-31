from django.urls import path

from shuttle.demultiplexer import Demultiplexer
from shuttle.utils.jwt_auth import JWTAuthMiddlewareStack
from shuttle.v2_consumers.fleet_terminal import TerminalConsumer

websocket_urlpatterns = [
    path("api/ws/v2/", JWTAuthMiddlewareStack(Demultiplexer.as_asgi())),
    path("api/ws/v2/fleet/terminal/<uuid:node_id>/", JWTAuthMiddlewareStack(TerminalConsumer.as_asgi())),
]
