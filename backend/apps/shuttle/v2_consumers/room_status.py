import asyncio
import time

from asgiref.sync import sync_to_async
from djangochannelsrestframework.observer.generics import action
from uvicorn.protocols.utils import ClientDisconnected

from main.models import Device, Room
from main.serializers.room_status import RoomLiveStatusSerializer
from shuttle.models import TsKvLatest
from shuttle.v2_consumers.base_generics import BaseGenericAsyncAPIConsumer

# One recompute of the aggregates costs ~24 ms and is the same for all of a tenant's
# subscribers, while group_send from publish_updates_batch arrives on every mq-async
# batch. Without a cache N open dashboards multiply the DB load N times and hit the DB
# limit before the broadcast itself. The cache is per process: there are few uvicorn
# workers, and a cross-process cache would cost a Redis round-trip on the same hot path.
_RESPONSE_TTL = 1.0
_response_cache: dict[str, tuple[float, dict]] = {}
_response_locks: dict[str, asyncio.Lock] = {}


class RoomStatusConsumer(BaseGenericAsyncAPIConsumer):
    queryset = TsKvLatest.objects.all()
    serializer_class = RoomLiveStatusSerializer

    # Deferred recompute on the falling edge (see _ensure_trailing_refresh).
    _trailing: asyncio.Task | None = None

    async def _compute_response(self, tenant_id):
        flag_counts = await sync_to_async(self.queryset.room_flag_counts)(tenant_id)  # pyright: ignore
        offline = await sync_to_async(Device.objects.offline_count)(tenant_id)
        checked_in = await sync_to_async(Room.objects.checked_in_count)(tenant_id)
        available = await sync_to_async(Room.objects.available_count)(tenant_id)

        base = {
            "available": available,
            "checkedin": checked_in,
            "offline": offline,
            **flag_counts,
        }
        serializer = self.serializer_class(instance=base)
        return serializer.data

    async def response(self, force: bool = False):
        """Tenant aggregates, at most one recompute per _RESPONSE_TTL per process.

        ``force`` skips the fast (pre-lock) cache hit so the deferred recompute
        always goes through the lock and re-evaluates freshness under it. The recompute
        itself stays coalesced (see the check under the lock).
        """
        tenant_id = str(self.tenant_id)
        cached = _response_cache.get(tenant_id)
        if not force and cached and time.monotonic() - cached[0] < _RESPONSE_TTL:
            return cached[1]

        lock = _response_locks.get(tenant_id)
        if lock is None:
            lock = _response_locks[tenant_id] = asyncio.Lock()
        async with lock:
            # Freshness is checked under the lock for the force path too: if a sibling coroutine
            # already recomputed in this window, reuse the result, so N dashboards
            # of one tenant = 1 recompute even on the deferred (trailing) path.
            # Correctness holds: trailing wakes up via asyncio.sleep(TTL),
            # i.e. not before the window ends, and the cache timestamp moves only on recompute,
            # so under the lock the cache age is either >= TTL (-> recompute) or the cache was just
            # refreshed by a sibling (-> it already reflects the window's changes).
            cached = _response_cache.get(tenant_id)
            if cached and time.monotonic() - cached[0] < _RESPONSE_TTL:
                return cached[1]

            data = await self._compute_response(self.tenant_id)
            _response_cache[tenant_id] = (time.monotonic(), data)
            return data

    async def _broadcast(self, data):
        for request_id, params in self.subscribers.items():
            if data == params.get("response"):
                continue
            await self.reply(data=data, action=params.get("action"), request_id=request_id)
            params["response"] = data

    def _ensure_trailing_refresh(self):
        """Catch up on the state after the cache window closes.

        Without this the last change might never arrive: if it fell into the window,
        the client got the cached value, and telemetry went quiet right after, then
        there is no next group_send and the dashboard stays with the stale number.
        """
        if self._trailing and not self._trailing.done():
            return
        self._trailing = asyncio.create_task(self._trailing_refresh())

    async def _trailing_refresh(self):
        try:
            await asyncio.sleep(_RESPONSE_TTL)
            if not self.subscribers:
                return
            data = await self.response(force=True)
            async with self._state_lock:
                if self.subscribers:
                    await self._broadcast(data)
        except asyncio.CancelledError:
            raise
        except (ClientDisconnected, RuntimeError):
            pass

    def _cancel_trailing(self):
        if self._trailing and not self._trailing.done():
            self._trailing.cancel()
        self._trailing = None

    async def get_latest_activity(self, message):
        if not self.subscribers:
            return
        await self._broadcast(await self.response())
        self._ensure_trailing_refresh()

    def cancel_background_tasks(self):
        super().cancel_background_tasks()
        self._cancel_trailing()

    async def disconnect(self, code):
        self._cancel_trailing()
        await super().disconnect(code)

    @action()
    async def list_subscribe(self, request_id, action, query_params):
        try:
            await self.add_group(f"room_status_{self.tenant_id}")
            res = await self.response()
            self.subscribers[request_id] = {"query_params": query_params, "action": action, "response": res}
            await self.reply(data=res, action=action, request_id=request_id)
        except (ClientDisconnected, RuntimeError):
            pass

    @action()
    async def list_unsubscribe(self, request_id, **kwargs):
        await self.remove_group(f"room_status_{self.tenant_id}")
        self.subscribers.pop(request_id, None)
        if not self.subscribers:
            self._cancel_trailing()
