import os

import django
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from channels.security.websocket import AllowedHostsOriginValidator
from django.urls import path

from apps.shuttle.consumers.shuttle import ShuttleConsumer

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

BASE_URLS = URLRouter([path("api/ws/", ShuttleConsumer.as_asgi())])

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": AllowedHostsOriginValidator(BASE_URLS),
    }
)
