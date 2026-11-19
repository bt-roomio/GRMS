import logging
import time

from asgiref.sync import sync_to_async
from djangochannelsrestframework.mixins import action

from core.utils.date import convert_datetime
from main.models import Device
from shuttle.models import TsKv
from shuttle.serializers.ts_kv_history import TsKvHistoryFilterParams, TsKvHistorySerializer
from shuttle.services.ts_kv_history_cache import get_or_compute, history_cache_key, history_cache_ttl
from shuttle.v2_consumers.base_generics import BaseGenericAsyncAPIConsumer

logger = logging.getLogger(__name__)


class TsKvHistoryConsumer(BaseGenericAsyncAPIConsumer):
    queryset = TsKv.objects.all()
    serializer_class = TsKvHistorySerializer
    # Telemetry arrives every few seconds and a refresh recomputes whole charts:
    # at most one live refresh per this many seconds (the last event is never lost).
    refresh_delay = 5.0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # request_id -> time of the latest telemetry event that subscription has not seen yet.
        self._pending_refresh: dict[str, float] = {}

    def resolve_params(self, query_params) -> tuple[dict, str | None]:
        """Validated params and the id of the device whose data the chart shows."""
        params = TsKvHistoryFilterParams.check(data=query_params or {})
        if params.get("room"):
            params["device"] = Device.objects.filter(
                room__id=params["room"], is_active=True, tenant_id=self.tenant_id
            ).first()
        device = params.get("device")
        return params, (str(device.pk) if device else None)

    def query_history(self, params):
        query = self.get_queryset().by_device(entity=params.get("device")).filter(entity__tenant_id=self.tenant_id)
        history = query.get_history_v2(  # ty: ignore
            keys=params.get("keys"),
            start_ts=convert_datetime(params.get("start_ts")) if params.get("start_ts") else None,
            interval=params.get("interval"),
            agg=params.get("agg"),
            limit=params.get("limit"),
            sort_by=params.get("sort_by"),
            auto_fill=params.get("auto_fill"),
        )
        return {
            key: [dict(item) for item in self.get_serializer(instance=rows, many=True, action_kwargs={}).data]
            for key, rows in history.items()
        }

    async def load_history(
        self, params, device_id, fresh_since: float | None = None, allow_stale: bool = False
    ) -> tuple[dict, bool]:
        """``(data, stale)``, see ``get_or_compute``."""
        key = history_cache_key(self.tenant_id, device_id, params) if device_id else None
        data, stale = await get_or_compute(
            key,
            device_id,
            history_cache_ttl(params.get("interval")),
            lambda: self.query_history(params),
            fresh_since=fresh_since,
            allow_stale=allow_stale,
        )
        # The cache is shared by requests listing the same keys in another order.
        return {key: data[key] for key in dict.fromkeys(params.get("keys") or []) if key in data}, stale

    async def ts_kv_activity(self, message):
        updates = message.get("updates") or [message.get("update")]
        changed = {
            (str(update.get("entity")), update.get("key"))
            for update in updates
            if isinstance(update, dict) and update.get("entity")
        }
        if not changed:
            return

        now = time.time()
        for request_id, subscription in self.subscribers.items():
            device_id = subscription["device_id"]
            if any((device_id, key) in changed for key in subscription["params"].get("keys") or []):
                self._pending_refresh[request_id] = now
        if self._pending_refresh:
            self.request_refresh(self.refresh_subscribers)

    async def refresh_subscribers(self):
        pending, self._pending_refresh = self._pending_refresh, {}
        for request_id, event_at in pending.items():
            subscription = self.subscribers.get(request_id)
            if subscription is None:
                continue
            try:
                # Subscriptions showing the same chart share one computation through the cache.
                data, _ = await self.load_history(subscription["params"], subscription["device_id"], event_at)
            except Exception:
                logger.exception("ts_kv_history: refresh of %s failed", request_id)
                continue
            # The current bucket may not have changed (same average): nothing to send.
            if data == subscription["response"]:
                continue
            subscription["response"] = data
            await self.reply(data=data, action=subscription["action"], request_id=request_id)

    def cancel_background_tasks(self):
        super().cancel_background_tasks()
        self._pending_refresh.clear()

    @action()
    async def list_subscribe(self, request_id, query_params, action):
        await self.check_device_access(query_params.get("device"))
        params, device_id = await sync_to_async(self.resolve_params)(query_params)
        if device_id:
            # Join the group before reading the data, so telemetry written in between is not missed.
            await self.add_group(f"tskv_updates_{device_id}")
        # A cached chart is sent at once even if the device has written since it was computed:
        # it is then recomputed in the background and the client gets the update.
        data, stale = await self.load_history(params, device_id, allow_stale=True)
        await self.reply(data=data, action=action, request_id=request_id)
        self.subscribers[request_id] = {
            "query_params": query_params,
            "params": params,
            "device_id": device_id,
            "action": action,
            "response": data,
        }
        if stale:
            self._pending_refresh[request_id] = time.time()
            self.request_refresh(self.refresh_subscribers)

    @action()
    async def list_unsubscribe(self, request_id, **kwargs):
        self.subscribers.pop(request_id, None)
        self._pending_refresh.pop(request_id, None)
