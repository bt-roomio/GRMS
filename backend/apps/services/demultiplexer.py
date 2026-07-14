import json

from channelsmultiplexer import AsyncJsonWebsocketDemultiplexer

from services.consumers.base import resolve_integration
from services.consumers.rooms import RoomsConsumer
from services.consumers.tags import RoomTagsConsumer, TagDetailConsumer


class Demultiplexer(AsyncJsonWebsocketDemultiplexer):
    applications = {
        "rooms": RoomsConsumer.as_asgi(),
        "room_tags": RoomTagsConsumer.as_asgi(),
        "tag": TagDetailConsumer.as_asgi(),
    }

    async def websocket_connect(self, message):
        integration = await resolve_integration(self.scope)
        if integration is None:
            await self.close(code=4401)
            return
        self.scope["integration"] = integration
        self.scope["tenant"] = integration.tenant
        await super().websocket_connect(message)

    async def websocket_receive(self, message):
        try:
            if "text" in message and message["text"]:
                content = json.loads(message["text"])
                await self.receive_json(content)
            else:
                raise ValueError("Non-JSON message received")
        except json.JSONDecodeError as e:
            await self.send_json(
                {
                    "stream": None,
                    "payload": {
                        "errors": [{"json": f"Invalid JSON: {str(e)}"}],
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
                    "errors": [{"stream": f"Invalid stream: {str(e)}"}],
                    "data": None,
                    "action": content.get("payload").get("action"),
                    "response_status": 400,
                    "request_id": content.get("payload").get("request_id"),
                },
            }
            await self.send_json(err)
