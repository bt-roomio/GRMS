import asyncio
import json
import logging
import threading

import pytest
from asgiref.sync import SyncToAsync, sync_to_async
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from djangochannelsrestframework.decorators import action
from uvicorn.protocols.utils import ClientDisconnected

from main.models import Room
from shuttle.demultiplexer import Demultiplexer
from shuttle.utils import demultiplexer as demux_module
from shuttle.utils.demultiplexer import LazyJsonWebsocketDemultiplexer
from shuttle.utils.log_filters import RedactTokenFilter
from shuttle.v2_consumers import room_status as rs
from shuttle.v2_consumers.base_generics import BaseGenericAsyncAPIConsumer
from users.models import User


@pytest.fixture(autouse=True)
def _clear_room_status_cache():
    rs._response_cache.clear()
    yield
    rs._response_cache.clear()


@pytest.fixture
@database_sync_to_async
def karina_tenant_id():
    return str(User.objects.get(email="karina@gmail.com").tenant_id)


def _frame(stream, action, request_id, **payload):
    return {"stream": stream, "payload": {"action": action, "request_id": request_id, **payload}}


@pytest.mark.asyncio
@pytest.mark.django_db(serialized_rollback=True)
class TestDemultiplexerIsolation:
    async def test_slow_db_call_does_not_block_other_connections(self, ws_connect, karina_token, monkeypatch):
        """A slow sync call from one socket must not delay its neighbours."""
        started, release = threading.Event(), threading.Event()

        def blocking_available_count(self, tenant_id):
            started.set()
            release.wait(10)
            return 0

        monkeypatch.setattr(type(Room.objects), "available_count", blocking_available_count)

        slow = await ws_connect(karina_token)
        fast = await ws_connect(karina_token)
        try:
            await slow.send_json_to(_frame("room_status", "list_subscribe", "slow", query_params={}))
            assert await asyncio.to_thread(started.wait, 5), "the slow socket request did not start"

            await fast.send_json_to(_frame("cards", "list", "fast", query_params={"page": 1, "size": 5}))
            reply = await fast.receive_json_from(timeout=3)
            assert reply["payload"]["request_id"] == "fast"
            assert reply["payload"]["response_status"] == 200
        finally:
            release.set()
            await slow.disconnect()
            await fast.disconnect()

    async def test_failing_group_handler_keeps_connection_alive(self, ws_connect, karina_token, karina_tenant_id):
        """A failing group_send handler must not drop the connection with all its streams."""
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(_frame("room_status", "list_subscribe", "rs1", query_params={}))
            await comm.receive_json_from(timeout=5)

            # There is no handler for this type: dispatch raises ValueError.
            await get_channel_layer().group_send(f"room_status_{karina_tenant_id}", {"type": "no.such.handler"})
            await asyncio.sleep(0.2)

            await comm.send_json_to(_frame("cards", "list", "after", query_params={"page": 1, "size": 5}))
            reply = await comm.receive_json_from(timeout=5)
            assert reply["payload"]["request_id"] == "after"
        finally:
            await comm.disconnect()

    async def test_streams_are_spawned_lazily(self, ws_connect, karina_token, monkeypatch):
        """A child consumer is created only for the stream that received a frame."""
        spawned = []

        def counting(name):
            app = Demultiplexer.applications[name]

            async def wrapper(scope, receive, send):
                spawned.append(name)
                return await app(scope, receive, send)

            return wrapper

        for name in ("cards", "rooms"):
            monkeypatch.setitem(Demultiplexer.applications, name, counting(name))

        comm = await ws_connect(karina_token)
        try:
            await asyncio.sleep(0.1)
            assert spawned == []

            for request_id in ("c1", "c2"):
                await comm.send_json_to(_frame("cards", "list", request_id, query_params={"page": 1, "size": 5}))
                reply = await comm.receive_json_from(timeout=5)
                assert reply["stream"] == "cards"
                assert reply["payload"]["request_id"] == request_id
            assert spawned == ["cards"]
        finally:
            await comm.disconnect()

    async def test_crashed_stream_is_respawned(self, ws_connect, karina_token, monkeypatch):
        """A crashed stream doesn't drop the socket and is respawned on the next frame."""
        app = Demultiplexer.applications["cards"]
        calls = []

        async def crash_once(scope, receive, send):
            calls.append(1)
            if len(calls) == 1:
                await receive()  # websocket.connect
                raise RuntimeError("boom")
            return await app(scope, receive, send)

        monkeypatch.setitem(Demultiplexer.applications, "cards", crash_once)

        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(_frame("cards", "list", "lost", query_params={"page": 1, "size": 5}))
            await asyncio.sleep(0.2)

            await comm.send_json_to(_frame("cards", "list", "ok", query_params={"page": 1, "size": 5}))
            reply = await comm.receive_json_from(timeout=5)
            assert reply["payload"]["request_id"] == "ok"
            assert len(calls) == 2
        finally:
            await comm.disconnect()

    async def test_unknown_stream_replies_error(self, ws_connect, karina_token):
        comm = await ws_connect(karina_token)
        try:
            await comm.send_json_to(_frame("no_such_stream", "list", "x1"))
            reply = await comm.receive_json_from(timeout=5)
            assert reply["stream"] == "no_such_stream"
            assert reply["payload"]["response_status"] == 400
            assert reply["payload"]["request_id"] == "x1"
        finally:
            await comm.disconnect()


@pytest.mark.asyncio
class TestDemultiplexerSend:
    def _demux(self, base_send):
        demux = Demultiplexer()
        demux.socket_closed = False
        demux.base_send = base_send
        return demux

    async def test_frame_wraps_stream_payload(self):
        sent = []

        async def base_send(message):
            sent.append(message)

        demux = self._demux(base_send)
        await demux._send_stream_frame("rooms", {"type": "websocket.send", "text": '{"data": [1]}'})
        assert [json.loads(m["text"]) for m in sent] == [{"stream": "rooms", "payload": {"data": [1]}}]

    async def test_send_after_close_is_dropped(self):
        sent = []

        async def base_send(message):
            sent.append(message)

        demux = self._demux(base_send)
        demux.socket_closed = True
        await demux._send_stream_frame("rooms", {"type": "websocket.send", "text": "{}"})
        assert sent == []

    @pytest.mark.parametrize(
        "exc",
        [
            ClientDisconnected(),
            RuntimeError(
                "Unexpected ASGI message 'websocket.send', after sending 'websocket.close' "
                "or response already completed."
            ),
        ],
    )
    async def test_send_to_closed_socket_is_swallowed(self, exc):
        async def base_send(message):
            raise exc

        demux = self._demux(base_send)
        await demux._send_stream_frame("rooms", {"type": "websocket.send", "text": "{}"})
        assert demux.socket_closed

    async def test_unrelated_runtime_error_propagates(self):
        async def base_send(message):
            raise RuntimeError("boom")

        demux = self._demux(base_send)
        with pytest.raises(RuntimeError, match="boom"):
            await demux._send_stream_frame("rooms", {"type": "websocket.send", "text": "{}"})


def test_redact_token_filter_masks_query_token():
    record = logging.LogRecord(
        "uvicorn.error",
        logging.INFO,
        __file__,
        0,
        '%s - "WebSocket %s" [accepted]',
        (("172.19.0.22", 5000), "/api/ws/v2/?token=eyJhbGci.payload.sig&x=1"),
        None,
    )
    assert RedactTokenFilter().filter(record)
    assert record.getMessage() == "('172.19.0.22', 5000) - \"WebSocket /api/ws/v2/?token=***&x=1\" [accepted]"


def test_redact_token_filter_keeps_mapping_args():
    record = logging.LogRecord(
        "uvicorn.error", logging.INFO, __file__, 0, "%(path)s", ({"path": "/ws/?token=abc"},), None
    )
    assert RedactTokenFilter().filter(record)
    assert record.getMessage() == "/ws/?token=***"


@pytest.mark.asyncio
async def test_ws_sync_pool_is_shared_and_closes_connections(monkeypatch):
    closed = []
    monkeypatch.setattr(demux_module, "close_old_connections", lambda: closed.append(1))

    token = SyncToAsync.thread_sensitive_context.set(demux_module.ws_sync_context())
    try:
        names = await asyncio.gather(*(sync_to_async(lambda: threading.current_thread().name)() for _ in range(4)))
    finally:
        SyncToAsync.thread_sensitive_context.reset(token)

    assert all(name.startswith("ws-sync") for name in names)
    assert len(closed) == 8  # before and after each call
    assert demux_module.ws_sync_context() is demux_module.ws_sync_context()


class _FakeConn:
    def __init__(self):
        self.connection = object()
        self.close_at = 0.0


def test_keep_connections_extends_only_new_connections(monkeypatch):
    fresh, reused, idle = _FakeConn(), _FakeConn(), _FakeConn()
    reused._ws_kept = reused.connection
    idle.connection = None
    monkeypatch.setattr(demux_module.connections, "all", lambda initialized_only: [fresh, reused, idle])

    demux_module._keep_connections(300)

    assert fresh.close_at > 0  # lifetime set on the first call after opening
    assert reused.close_at == 0.0  # an already extended connection isn't extended forever
    assert idle.close_at == 0.0

    fresh.connection = object()  # connection reopened: new lifetime
    fresh.close_at = 0.0
    demux_module._keep_connections(300)
    assert fresh.close_at > 0


def test_keep_connections_disabled(monkeypatch):
    conn = _FakeConn()
    monkeypatch.setattr(demux_module.connections, "all", lambda initialized_only: [conn])
    demux_module._keep_connections(0)
    assert conn.close_at == 0.0


@pytest.mark.asyncio
async def test_refresh_waits_for_running_handler():
    """A deferred refresh doesn't overlap with a message handler."""
    consumer = BaseGenericAsyncAPIConsumer()
    consumer.refresh_delay = 0
    calls = []

    async def refresh():
        calls.append(1)

    async with consumer._state_lock:
        consumer.request_refresh(refresh)
        consumer.request_refresh(refresh)  # coalesced with the first one
        await asyncio.sleep(0.05)
        assert calls == []

    await asyncio.sleep(0.05)
    assert calls == [1]  # both events arrived before the refresh, so it runs once


@pytest.mark.asyncio
async def test_cancelled_consumer_cancels_background_tasks():
    consumer = BaseGenericAsyncAPIConsumer()
    consumer.refresh_delay = 10

    async def refresh():
        pass

    consumer.request_refresh(refresh, key="slow")
    task = consumer._refresh_tasks["slow"]

    consumer.cancel_background_tasks()
    await asyncio.sleep(0)
    assert task.cancelled()
    assert consumer._refresh_tasks == {}


class _StuckStream(BaseGenericAsyncAPIConsumer):
    permission_classes = []
    gate = threading.Event()

    @action()
    async def join(self, **kwargs):
        await self.add_group("stuck_group")
        return {}, 200

    @action()
    async def hang(self, **kwargs):
        await sync_to_async(self.gate.wait)(5)
        return {}, 200


class _StuckDemux(LazyJsonWebsocketDemultiplexer):
    applications = {"stuck": _StuckStream.as_asgi()}
    application_close_timeout = 0.2


@pytest.mark.asyncio
async def test_cancelled_stream_leaves_its_groups():
    """A stream that didn't get to handle disconnect is cancelled and still leaves its groups."""
    _StuckStream.gate.clear()
    comm = WebsocketCommunicator(_StuckDemux.as_asgi(), "/")
    comm.scope["user"] = {"id": 1, "tenant_id": "t"}
    assert (await comm.connect())[0]
    layer = get_channel_layer()
    try:
        await comm.send_json_to(_frame("stuck", "join", "j"))
        await comm.receive_json_from(timeout=2)
        assert len(layer.groups.get("stuck_group", {})) == 1

        await comm.send_json_to(_frame("stuck", "hang", "h"))
        await asyncio.sleep(0.1)
        await comm.disconnect(timeout=3)
    finally:
        _StuckStream.gate.set()

    assert not layer.groups.get("stuck_group")
