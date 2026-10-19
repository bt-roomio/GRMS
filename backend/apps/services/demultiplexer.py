from services.consumers.base import resolve_integration
from services.consumers.rooms import RoomsConsumer
from services.consumers.tags import RoomTagsConsumer, TagDetailConsumer
from shuttle.utils.demultiplexer import LazyJsonWebsocketDemultiplexer


class Demultiplexer(LazyJsonWebsocketDemultiplexer):
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
        # Child consumers are created later and get a copy of the scope that already has the integration.
        self.scope["integration"] = integration
        self.scope["tenant"] = integration.tenant
        await super().websocket_connect(message)
