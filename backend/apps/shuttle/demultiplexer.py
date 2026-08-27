import json

from channelsmultiplexer import AsyncJsonWebsocketDemultiplexer

from shuttle.v2_consumers.attributes import AttributeConsumer
from shuttle.v2_consumers.card_logs import CardLogConsumer
from shuttle.v2_consumers.cards import CardConsumer
from shuttle.v2_consumers.devices import DevicesListConsumer
from shuttle.v2_consumers.emergency_status import EmergencyStatus
from shuttle.v2_consumers.fleet_nodes import FleetNodeConsumer
from shuttle.v2_consumers.gateway import GatewayConsumer
from shuttle.v2_consumers.gateway_logs import GatewayLogsConsumer
from shuttle.v2_consumers.guest_cards import GuestCardConsumer
from shuttle.v2_consumers.guests import GuestConsumer
from shuttle.v2_consumers.inactive_attributes import InactiveDeviceAttributeConsumer
from shuttle.v2_consumers.need_sync import NeedSyncConsumer
from shuttle.v2_consumers.room_detail import RoomDetailConsumer
from shuttle.v2_consumers.room_dynamics import TsKvTenantHistoryConsumer
from shuttle.v2_consumers.room_status import RoomStatusConsumer
from shuttle.v2_consumers.rooms import RoomConsumer
from shuttle.v2_consumers.scanned_devices import ScannedDevicesConsumer
from shuttle.v2_consumers.tag_logs import TagLogsConsumer
from shuttle.v2_consumers.ts_kv_history import TsKvHistoryConsumer
from shuttle.v2_consumers.ts_kv_latest import TsKvLatestConsumer


class Demultiplexer(AsyncJsonWebsocketDemultiplexer):
    applications = {
        "rooms": RoomConsumer.as_asgi(),
        "room_detail": RoomDetailConsumer.as_asgi(),
        "room_status": RoomStatusConsumer.as_asgi(),
        "devices": DevicesListConsumer.as_asgi(),
        "scanned_devices": ScannedDevicesConsumer.as_asgi(),
        "guests": GuestConsumer.as_asgi(),
        "guest_cards": GuestCardConsumer.as_asgi(),
        "cards": CardConsumer.as_asgi(),
        "card_logs": CardLogConsumer.as_asgi(),
        "attributes": AttributeConsumer.as_asgi(),
        "current_alarms": InactiveDeviceAttributeConsumer.as_asgi(),
        "gateway_logs": GatewayLogsConsumer.as_asgi(),
        "gateways": GatewayConsumer.as_asgi(),
        "tag_logs": TagLogsConsumer.as_asgi(),
        "tskv_tenant_history": TsKvTenantHistoryConsumer.as_asgi(),
        "ts_kv_history": TsKvHistoryConsumer.as_asgi(),
        "ts_kv_latest": TsKvLatestConsumer.as_asgi(),
        "emergency_status": EmergencyStatus.as_asgi(),
        "need_sync": NeedSyncConsumer.as_asgi(),
        "fleet_nodes": FleetNodeConsumer.as_asgi(),
    }

    async def websocket_receive(self, message):
        try:
            if message.get("text"):
                content = json.loads(message["text"])
                await self.receive_json(content)
            else:
                raise ValueError("Non-JSON message received")
        except json.JSONDecodeError as e:
            await self.send_json(
                {
                    "stream": None,
                    "payload": {
                        "errors": [{"json": f"Invalid JSON: {e!s}"}],
                        "data": None,
                        "action": None,
                        "response_status": 400,
                        "request_id": None,
                    },
                }
            )
        except Exception as e:
            await self.send_json(
                {
                    "stream": None,
                    "payload": {
                        "errors": [{"general": str(e)}],
                        "data": None,
                        "action": None,
                        "response_status": 400,
                        "request_id": None,
                    },
                }
            )

    async def receive_json(self, content, **kwargs):
        try:
            await super().receive_json(content, **kwargs)
        except ValueError as e:
            err = {
                "stream": content.get("stream"),
                "payload": {
                    "errors": [{"stream": f"Invalid stream: {e!s}"}],
                    "data": None,
                    "action": content.get("payload").get("action"),
                    "response_status": 400,
                    "request_id": content.get("payload").get("request_id"),
                },
            }
            await self.send_json(err)
