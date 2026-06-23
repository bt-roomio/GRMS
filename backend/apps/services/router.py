from django.urls import path

from services.demultiplexer import Demultiplexer

websocket_urlpatterns = [
    # services endpoint: no token middleware (no auth)
    path("api/ws/v1/services/", Demultiplexer.as_asgi()),
]
