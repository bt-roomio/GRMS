import asyncio
import contextlib
import json
import logging
from collections.abc import Awaitable, Callable
from uuid import UUID

from asgiref.sync import sync_to_async
from channels.exceptions import StopConsumer
from django.core.exceptions import ValidationError as DjangoValidationError
from djangochannelsrestframework.generics import GenericAsyncAPIConsumer

from rest_framework.exceptions import NotFound

from main.models import Device
from users.models import User

logger = logging.getLogger(__name__)


class UUIDEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, UUID):
            return o.hex
        return json.JSONEncoder.default(self, o)


class BaseGenericAsyncAPIConsumer(GenericAsyncAPIConsumer):
    pagination_class = None
    # Event coalescing window for request_refresh, seconds.
    refresh_delay = 0.3

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._refresh_tasks: dict[str, asyncio.Task] = {}
        self._refresh_dirty: set[str] = set()
        self._tenant_devices: set[str] = set()
        # Message handlers and deferred refreshes work on the same
        # state (subscribers, responses, groups), so they run one at a time.
        self._state_lock = asyncio.Lock()
        self._groups_released = False

    async def __call__(self, scope, receive, send):
        try:
            await super().__call__(scope, receive, send)
        finally:
            # The demultiplexer may cancel the consumer task directly (stop
            # timeout, refused stream), and then websocket_disconnect is not called.
            self.cancel_background_tasks()
            for task in self.detached_tasks:
                task.cancel()
            if not self._groups_released and getattr(self, "channel_layer", None) is not None:
                # Otherwise the channel would stay in the groups until group_expiry (a day),
                # and group_send would keep sending messages to it.
                for group in list(self.groups):
                    with contextlib.suppress(Exception):
                        await self.channel_layer.group_discard(group, self.channel_name)

    async def dispatch(self, message):
        if message.get("type") == "websocket.disconnect":
            # Don't wait for a long refresh holding the lock: it is no longer needed anyway.
            self.cancel_background_tasks()
            self._groups_released = True
        async with self._state_lock:
            try:
                await super().dispatch(message)
            except StopConsumer:
                raise
            except Exception:
                # A child consumer lives inside the demultiplexer: if its task
                # crashes, the client loses this stream until the next frame to it.
                # So a failure of one handler (client action or group_send)
                # is logged and the remaining subscriptions keep being served.
                if message.get("type") in ("websocket.connect", "websocket.disconnect"):
                    raise
                logger.exception("WS %s: handler for %r failed", type(self).__name__, message.get("type"))

    async def accept(self, *args, **kwargs):
        self.subscribers = {}
        await super().accept(*args, **kwargs)

    def cancel_background_tasks(self):
        """Cancel the consumer's background tasks; called on any exit."""
        for task in self._refresh_tasks.values():
            task.cancel()
        self._refresh_tasks.clear()
        self._refresh_dirty.clear()

    def request_refresh(self, refresh: Callable[[], Awaitable], key: str | None = None):
        """Run ``refresh`` once per burst of events rather than once per event.

        group_send "re-read the list" handlers used to run a full DB query
        for every message and every subscription; mq-async and signals send them
        in bursts. Here the first event defers the refresh by ``refresh_delay``,
        further events within the window are absorbed, and those arriving during the
        refresh trigger one more, final run.

        The refresh runs as a separate task, but under the same lock as the message
        handlers: it doesn't overlap with list_subscribe/unsubscribe and reads
        subscriptions as they are at the moment it runs.
        """
        key = key or getattr(refresh, "__name__", repr(refresh))
        task = self._refresh_tasks.get(key)
        if task is not None and not task.done():
            self._refresh_dirty.add(key)
            return
        self._refresh_tasks[key] = asyncio.create_task(self._run_refresh(key, refresh))

    async def _run_refresh(self, key, refresh):
        while True:
            await asyncio.sleep(self.refresh_delay)
            async with self._state_lock:
                self._refresh_dirty.discard(key)
                try:
                    await refresh()
                except Exception:
                    logger.exception("WS %s: refresh %r failed", type(self).__name__, key)
            if key not in self._refresh_dirty:
                return

    async def check_device_access(self, device_id):
        """Prevent subscribing to a device of another tenant.

        ``*_{device_id}`` groups know nothing about tenants, and without this check a client got
        live telemetry of any device whose id it knew.
        """
        if not device_id:
            return
        key = str(device_id)
        if key in self._tenant_devices:
            return
        try:
            allowed = await sync_to_async(Device.objects.filter(pk=key, tenant_id=self.tenant_id).exists)()
        except (DjangoValidationError, ValueError):
            allowed = False
        if not allowed:
            raise NotFound("Device not found!")
        self._tenant_devices.add(key)

    @classmethod
    async def encode_json(cls, content):
        return json.dumps(content, cls=UUIDEncoder)

    @property
    def user_id(self):
        if isinstance(self.scope["user"], dict):
            return self.scope["user"].get("id")
        return self.scope["user"].id

    @property
    def tenant_id(self):
        if isinstance(self.scope["user"], dict):
            return self.scope["user"].get("tenant_id")
        return self.scope["user"].tenant_id

    def get_user_object(self):
        return User.objects.filter(pk=self.scope["user"].id, is_active=True).first()

    def get_user(self):
        return User.objects.filter(pk=self.scope["user"].id, is_active=True).values().first()

    def get_data_paginated(self, query_params, **kwargs):
        queryset = self.get_queryset(query_params=query_params)
        count = queryset.count()
        queryset = self.pagination(queryset, query_params.get("page", 1), query_params.get("size", 15))
        serializer = self.get_serializer(instance=queryset, many=True, action_kwargs=kwargs)
        return {"results": serializer.data, "count": count}

    async def send_list_paginated(self, action, query_params, request_id, **kwargs):
        data = await sync_to_async(self.get_data_paginated)(query_params=query_params, **kwargs)
        await self.reply(data=data, action=action, request_id=request_id)
        return data

    def get_data(self, **kwargs):
        queryset = self.get_queryset(query_params=kwargs.get("query_params"))
        serializer = self.get_serializer(instance=queryset, many=True, action_kwargs=kwargs)
        return serializer.data

    async def send_list(self, action, query_params, request_id, **kwargs):
        data = await sync_to_async(self.get_data)(query_params=query_params, **kwargs)
        await self.reply(data=data, action=action, request_id=request_id)
        return data

    def pagination(self, queryset, page, size=15):
        page = page or 1
        offset = (page - 1) * size
        limit = offset + size
        queryset = queryset[offset:limit]
        return queryset
