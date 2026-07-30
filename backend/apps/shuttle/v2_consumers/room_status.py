import asyncio
import time

from asgiref.sync import sync_to_async
from djangochannelsrestframework.observer.generics import action
from uvicorn.protocols.utils import ClientDisconnected

from main.models import Device, Room
from main.serializers.room_status import RoomLiveStatusSerializer
from shuttle.models import TsKvLatest
from shuttle.v2_consumers.base_generics import BaseGenericAsyncAPIConsumer

# Один пересчёт агрегатов стоит ~24 мс и одинаков для всех подписчиков тенанта, а
# group_send из publish_updates_batch прилетает на каждый батч mq-async. Без кеша
# N открытых дашбордов множат нагрузку на БД в N раз и упираются в неё раньше, чем
# в саму рассылку. Кеш процессный: воркеров uvicorn немного, а межпроцессный кеш
# стоил бы round-trip в Redis на том же горячем пути.
_RESPONSE_TTL = 1.0
_response_cache: dict[str, tuple[float, dict]] = {}
_response_locks: dict[str, asyncio.Lock] = {}


class RoomStatusConsumer(BaseGenericAsyncAPIConsumer):
    queryset = TsKvLatest.objects.all()
    serializer_class = RoomLiveStatusSerializer

    # Отложенный пересчёт по спадающему фронту (см. _ensure_trailing_refresh).
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
        """Агрегаты тенанта, не чаще одного пересчёта в _RESPONSE_TTL на процесс.

        ``force`` пропускает быстрый (до-локовый) хит кеша, чтобы отложенный пересчёт
        всегда проходил через лок и переоценивал свежесть под ним. Сам пересчёт
        при этом остаётся коалесцированным (см. проверку под локом).
        """
        tenant_id = str(self.tenant_id)
        cached = _response_cache.get(tenant_id)
        if not force and cached and time.monotonic() - cached[0] < _RESPONSE_TTL:
            return cached[1]

        lock = _response_locks.get(tenant_id)
        if lock is None:
            lock = _response_locks[tenant_id] = asyncio.Lock()
        async with lock:
            # Под локом свежесть проверяем и для force-пути: если соседняя корутина
            # уже пересчитала в этом окне, переиспользуем результат — так N дашбордов
            # одного тенанта = 1 пересчёт даже на отложенном (trailing) пути.
            # Корректность сохраняется: trailing просыпается через asyncio.sleep(TTL),
            # то есть не раньше окна, а метка кеша сдвигается только при пересчёте —
            # значит под локом возраст кеша ≥ TTL (→ пересчёт) либо кеш только что
            # обновлён соседом (→ уже отражает изменения окна).
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
        """Досчитать состояние после закрытия окна кеша.

        Без этого последнее изменение могло бы не доехать: если оно попало в окно,
        клиент получил закешированное значение, а телеметрия сразу стихла, то
        следующего group_send не будет и дашборд останется со старой цифрой.
        """
        if self._trailing and not self._trailing.done():
            return
        self._trailing = asyncio.create_task(self._trailing_refresh())

    async def _trailing_refresh(self):
        try:
            await asyncio.sleep(_RESPONSE_TTL)
            if not self.subscribers:
                return
            await self._broadcast(await self.response(force=True))
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
