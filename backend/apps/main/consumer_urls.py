from channels.routing import URLRouter
from django.urls import path

from main.consumers.device import DeviceConsumer
from main.consumers.room import RoomConsumer


main_consumer_urls = URLRouter(
    [
        path("devices/", DeviceConsumer.as_asgi(), name="device-list"),
        path("room/", RoomConsumer.as_asgi(), name="room-list"),
    ]
)
