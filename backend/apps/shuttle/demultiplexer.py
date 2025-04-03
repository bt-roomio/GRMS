from channelsmultiplexer import AsyncJsonWebsocketDemultiplexer

from shuttle.v2_consumers.rooms import RoomConsumer
from shuttle.v2_consumers.ts_kv_history import TsKvConsumer


class Demultiplexer(AsyncJsonWebsocketDemultiplexer):
    applications = {
        "rooms": RoomConsumer.as_asgi(),
        "ts_kv_history": TsKvConsumer.as_asgi(),
    }
