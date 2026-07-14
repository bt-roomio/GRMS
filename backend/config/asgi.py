import os

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Initialise the Django ASGI application first. This populates the app registry,
# so it must run before importing any code (the routers and their consumers) that
# touches models.
django_asgi_app = get_asgi_application()

from services.router import websocket_urlpatterns as services_websocket_urlpatterns  # noqa: E402
from shuttle.router import websocket_urlpatterns as shuttle_websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            URLRouter(
                [
                    *shuttle_websocket_urlpatterns,
                    *services_websocket_urlpatterns,
                ]
            )
        ),
    }
)
