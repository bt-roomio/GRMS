from channelsmultiplexer import AsyncJsonWebsocketDemultiplexer

from shuttle.v2_consumers.attributes import AttributeConsumer
from shuttle.v2_consumers.guest_cards import GuestCardConsumer
from shuttle.v2_consumers.emergency_status import EmergencyStatus
from shuttle.v2_consumers.gateway_logs import GatewayLogsConsumer
from shuttle.v2_consumers.guests import GuestConsumer
from shuttle.v2_consumers.room_status import RoomStatusConsumer
from shuttle.v2_consumers.rooms import RoomConsumer
from shuttle.v2_consumers.tag_logs import TagLogsConsumer
from shuttle.v2_consumers.ts_kv_history import TsKvHistoryConsumer
from shuttle.v2_consumers.ts_kv_latest import TsKvLatestConsumer


class Demultiplexer(AsyncJsonWebsocketDemultiplexer):
    applications = {
        "rooms": RoomConsumer.as_asgi(),
        "guests": GuestConsumer.as_asgi(),
        "guest_cards": GuestCardConsumer.as_asgi(),
        "attributes": AttributeConsumer.as_asgi(),
        "ts_kv_latest": TsKvLatestConsumer.as_asgi(),
        "gateway_logs": GatewayLogsConsumer.as_asgi(),
        "tag_logs": TagLogsConsumer.as_asgi(),
        "ts_kv_history": TsKvHistoryConsumer.as_asgi(),
        "room_status": RoomStatusConsumer.as_asgi(),
        "emergency_status": EmergencyStatus.as_asgi(),
    }
