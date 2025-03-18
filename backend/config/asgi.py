import os

import django
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application
from django.urls import path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.shuttle.consumers.receiver import ReceiverConsumer  # noqa: E402

BASE_URLS = URLRouter([path("api/ws/", ReceiverConsumer.as_asgi())])  # noqa: F821  # pyright: ignore

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": AllowedHostsOriginValidator(BASE_URLS),
    }
)
