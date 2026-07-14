from django.urls import path

from shuttle.demultiplexer import Demultiplexer
from shuttle.utils.jwt_auth import JWTAuthMiddlewareStack

websocket_urlpatterns = [
    path("api/ws/v2/", JWTAuthMiddlewareStack(Demultiplexer.as_asgi())),
]
