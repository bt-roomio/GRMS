from channels.routing import URLRouter
from django.urls import path

from shuttle.consumers.shuttle import ShuttleConsumer


routes = URLRouter([path("", ShuttleConsumer.as_asgi(), name="shuttle")])
