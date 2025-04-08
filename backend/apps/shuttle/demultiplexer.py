from channelsmultiplexer import AsyncJsonWebsocketDemultiplexer

from shuttle.v2_consumers.attributes import AttributeConsumer
from shuttle.v2_consumers.gateway_logs import GatewayLogsConsumer
from shuttle.v2_consumers.guests import GuestConsumer
from shuttle.v2_consumers.rooms import RoomConsumer
from shuttle.v2_consumers.ts_kv_latest import TsKvLatestConsumer


class Demultiplexer(AsyncJsonWebsocketDemultiplexer):
    applications = {
        "rooms": RoomConsumer.as_asgi(),
        "guests": GuestConsumer.as_asgi(),
        "attributes": AttributeConsumer.as_asgi(),
        "ts_kv_latest": TsKvLatestConsumer.as_asgi(),
        "gateway_logs": GatewayLogsConsumer.as_asgi(),
    }
