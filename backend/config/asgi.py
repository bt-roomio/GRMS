import os

import django
from channels.routing import ProtocolTypeRouter
from django.core.asgi import get_asgi_application

from apps.shuttle.router import websocket_urlpatterns

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

application = ProtocolTypeRouter({"http": get_asgi_application(), "websocket": websocket_urlpatterns})
