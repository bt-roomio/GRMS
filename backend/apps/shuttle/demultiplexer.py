from channelsmultiplexer import AsyncJsonWebsocketDemultiplexer

from shuttle.v2_consumers.rooms import RoomConsumer


class Demultiplexer(AsyncJsonWebsocketDemultiplexer):
    applications = {
        "rooms": RoomConsumer.as_asgi(),
    }
