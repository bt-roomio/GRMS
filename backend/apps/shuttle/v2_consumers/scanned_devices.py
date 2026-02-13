from asgiref.sync import sync_to_async
from djangochannelsrestframework.observer.generics import action

from shuttle.consumers.aggregations.scanned_devices import main_scanned_devices
from shuttle.v2_consumers.base_generics import BaseGenericAsyncAPIConsumer


class ScannedDevicesConsumer(BaseGenericAsyncAPIConsumer):
    async def accept(self, *args, **kwargs):
        self.subscribers = {}
        await super().accept(*args, **kwargs)

    def _build_cmd(self, request_id, query_params):
        return {
            "cmd_id": request_id,
            "entity_id": query_params.get("entity_id"),
            "connector_name": query_params.get("connector_name"),
            "query": query_params.get("query", {}),
        }

    async def fetch_and_reply(self, request_id, action_name, query_params):
        user = await sync_to_async(self.get_user_object)()
        if not user:
            return
        cmd = self._build_cmd(request_id, query_params)
        result = await main_scanned_devices(cmd, [], user)
        await self.reply(data=result["data"], action=action_name, request_id=request_id)

    @action()
    async def list(self, request_id, action, query_params, **kwargs):
        await self.fetch_and_reply(request_id, action, query_params)

    async def get_latest_activity(self, message):
        update = message.get("update") or {}
        entity = update.get("entity")
        scope = update.get("scope")
        key_name = update.get("key_name")
        relevant_keys = {"scanned_devices", "upload_status", "scan_status"}

        for request_id, params in self.subscribers.items():
            query_params = params.get("query_params", {})
            sub_entity = query_params.get("entity_id")
            sub_connector = query_params.get("connector_name")

            is_relevant = (
                entity == sub_entity
                or (scope == "CLIENT_SCOPE" and key_name in relevant_keys)
                or (scope == "SHARED_SCOPE" and key_name == sub_connector)
            )

            if is_relevant:
                await self.fetch_and_reply(request_id, params["action"], query_params)

    @action()
    async def list_subscribe(self, request_id, action, query_params, **kwargs):
        await self.fetch_and_reply(request_id, action, query_params)
        await self.add_group(f"attribute_kv_updates_{self.tenant_id}")
        self.subscribers[request_id] = {"query_params": query_params, "action": action}

    @action()
    async def list_unsubscribe(self, request_id, **kwargs):
        self.subscribers.pop(request_id, None)
        if not self.subscribers:
            await self.remove_group(f"attribute_kv_updates_{self.tenant_id}")
