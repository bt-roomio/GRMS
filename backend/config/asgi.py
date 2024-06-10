import os

import django
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from channels.security.websocket import AllowedHostsOriginValidator
from django.urls import path

from apps.users.utils.jwt_auth import JWTAuthMiddlewareStack
from apps.main.consumer_urls import main_consumer_urls

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

BASE_URLS = URLRouter([path("api/v1/", URLRouter([path("main/", main_consumer_urls)]))])

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": AllowedHostsOriginValidator(JWTAuthMiddlewareStack(BASE_URLS)),
    }
)
