from channelsmultiplexer import AsyncJsonWebsocketDemultiplexer

from shuttle.v2_consumers.attributes import AttributeConsumer
from shuttle.v2_consumers.rooms import RoomConsumer
from shuttle.v2_consumers.ts_kv_history import TsKvConsumer
from shuttle.v2_consumers.ts_kv_latest import TsKvLatestConsumer


class Demultiplexer(AsyncJsonWebsocketDemultiplexer):
    applications = {
        "rooms": RoomConsumer.as_asgi(),
        "attributes": AttributeConsumer.as_asgi(),
        "ts_kv_latest": TsKvLatestConsumer.as_asgi(),
        "ts_kv_history": TsKvConsumer.as_asgi(),
    }
