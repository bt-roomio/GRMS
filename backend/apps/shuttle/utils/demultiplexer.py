import asyncio
import json
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from asgiref.sync import SyncToAsync, ThreadSensitiveContext
from channels.exceptions import StopConsumer
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.conf import settings
from django.db import close_old_connections, connections
from uvicorn.protocols.utils import ClientDisconnected

logger = logging.getLogger(__name__)


def _call_with_db_connections(fn, *args):
    # A pool thread serves calls from different sockets interleaved: a broken connection,
    # or one with an unfinished transaction, must not be handed to the next call.
    close_old_connections()
    try:
        return fn(*args)
    finally:
        _keep_connections(settings.WS_DB_CONN_MAX_AGE)
        close_old_connections()


def _keep_connections(max_age):
    """Extend the lifetime of connections opened in this thread to ``max_age`` seconds.

    The global CONN_MAX_AGE=0 is meant for HTTP (a thread per request) and would close
    the connection after every call. The lifetime is set once, when the connection
    is opened: from then on close_old_connections closes it when it expires, after an
    error, or if the call didn't restore autocommit. Before reuse Django checks the
    connection (CONN_HEALTH_CHECKS).
    """
    if not max_age:
        return
    for conn in connections.all(initialized_only=True):
        raw = conn.connection
        if raw is not None and getattr(conn, "_ws_kept", None) is not raw:
            conn._ws_kept = raw
            conn.close_at = time.monotonic() + max_age


class _SyncPool(ThreadPoolExecutor):
    def submit(self, fn, /, *args, **kwargs):
        return super().submit(_call_with_db_connections, fn, *args, **kwargs)


# Thread-sensitive call context shared by all WS connections of the process.
# Without it channels sends sync_to_async(thread_sensitive=True) to ONE shared
# asgiref thread, and a slow query from one client stalled every socket of the worker.
# A thread per connection fixed that at the cost of ~1000 threads per worker, hence a
# bounded pool here. The context is registered in asgiref once and never
# "exited", otherwise ThreadSensitiveContext.__aexit__ would shut down the shared pool.
_ws_sync_context: ThreadSensitiveContext | None = None
_ws_sync_context_lock = threading.Lock()


def ws_sync_context() -> ThreadSensitiveContext:
    global _ws_sync_context
    with _ws_sync_context_lock:
        if _ws_sync_context is None:
            context = ThreadSensitiveContext()
            SyncToAsync.context_to_thread_executor[context] = _SyncPool(
                max_workers=settings.WS_SYNC_THREADS, thread_name_prefix="ws-sync"
            )
            _ws_sync_context = context
        return _ws_sync_context


@dataclass
class _Stream:
    queue: asyncio.Queue
    task: asyncio.Task | None = None
    closed: bool = False


class LazyJsonWebsocketDemultiplexer(AsyncJsonWebsocketConsumer):
    """One socket, many streams: ``{"stream": <name>, "payload": {...}}``.

    A stream's child consumer is created lazily, on the first frame to that stream, rather
    than all at once on every connect (as in channelsmultiplexer): a client usually needs
    2-3 streams out of twenty-odd, and each child consumer is an asyncio task
    and its own channel in the channel layer.

    Child consumers are isolated: a crash of one is logged and doesn't drop the connection,
    the next frame to that stream respawns it.
    """

    # Stream name -> ASGI application of the child consumer.
    applications: dict = {}
    # The demultiplexer itself needs no channel layer: group_send targets the children.
    channel_layer_alias = "__demultiplexer_has_no_channel_layer__"
    application_close_timeout = 5

    async def __call__(self, scope, receive, send):
        self.streams: dict[str, _Stream] = {}
        self.socket_closed = False
        # Child consumers are created inside and inherit the context via contextvars.
        token = SyncToAsync.thread_sensitive_context.set(ws_sync_context())
        try:
            await super().__call__(scope, receive, send)
        finally:
            await self._stop_streams()
            SyncToAsync.thread_sensitive_context.reset(token)

    # --- client -> stream ---

    async def websocket_connect(self, message):
        await self.accept()

    async def websocket_disconnect(self, message):
        self.socket_closed = True
        await self._stop_streams(message)
        raise StopConsumer()

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
        if not isinstance(content, dict) or "stream" not in content or "payload" not in content:
            raise ValueError("Invalid multiplexed frame received (no stream/payload key)")

        stream_name, payload = content["stream"], content["payload"]
        stream = self._get_stream(stream_name)
        if stream is None:
            await self._reply_stream_error(content, "Invalid multiplexed frame received (stream not mapped)")
            return

        await stream.queue.put({"type": "websocket.receive", "text": await self.encode_json(payload)})

    def _get_stream(self, name) -> _Stream | None:
        app = self.applications.get(name) if isinstance(name, str) else None
        if app is None:
            return None

        stream = self.streams.get(name)
        if stream is not None:
            return None if stream.closed else stream

        stream = _Stream(queue=asyncio.Queue())
        stream.queue.put_nowait({"type": "websocket.connect"})
        # The task inherits the current context, and with it the thread pool.
        stream.task = asyncio.create_task(
            app(dict(self.scope), stream.queue.get, lambda message, _name=name: self._from_stream(_name, message)),
            name=f"ws-stream-{name}",
        )
        stream.task.add_done_callback(lambda task, _name=name: self._on_stream_done(_name, task))
        self.streams[name] = stream
        return stream

    async def _reply_stream_error(self, content, error):
        payload = content.get("payload") if isinstance(content.get("payload"), dict) else {}
        await self.send_json(
            {
                "stream": content.get("stream"),
                "payload": {
                    "errors": [{"stream": f"Invalid stream: {error}"}],
                    "data": None,
                    "action": payload.get("action"),
                    "response_status": 400,
                    "request_id": payload.get("request_id"),
                },
            }
        )

    # --- stream -> client ---

    async def _from_stream(self, name, message):
        msg_type = message.get("type")
        if msg_type == "websocket.send":
            await self._send_stream_frame(name, message)
        elif msg_type == "websocket.close":
            # The stream refused to work (e.g. DCRF rejected connect on permissions).
            # The socket stays open for the other streams, and further frames to this stream
            # get an error.
            stream = self.streams.get(name)
            if stream is not None:
                stream.closed = True
                if stream.task is not None:
                    stream.task.cancel()
        # websocket.accept: the socket was already accepted by the demultiplexer on connect.

    async def _send_stream_frame(self, name, message):
        # The child consumer may finish a reply after the socket is closed: disconnect
        # reaches it through the queue while it waits on the DB. Such a send is pointless,
        # and the exception from it kills the child task and clutters the logs.
        if self.socket_closed:
            return
        text = message.get("text")
        if text is None:
            return
        # The payload is already serialized by the child consumer: wrap it as a string,
        # without re-running json.loads/json.dumps on large lists.
        frame = f'{{"stream": {json.dumps(name)}, "payload": {text}}}'
        try:
            await self.send(text_data=frame)
        except ClientDisconnected:
            self.socket_closed = True
        except RuntimeError as exc:
            if "after sending 'websocket.close'" not in str(exc):
                raise
            self.socket_closed = True

    # --- stream lifecycle ---

    def _on_stream_done(self, name, task: asyncio.Task):
        stream = self.streams.get(name)
        # Drop a crashed stream so the next frame respawns it; keep a closed
        # (refused) one marked.
        if stream is not None and stream.task is task and not stream.closed:
            del self.streams[name]
        if task.cancelled():
            return
        exc = task.exception()
        if exc is not None and not isinstance(exc, StopConsumer):
            logger.error("WS stream %r crashed", name, exc_info=exc)

    async def _stop_streams(self, disconnect_message=None):
        streams = list(self.streams.values())
        self.streams.clear()
        tasks = [s.task for s in streams if s.task is not None and not s.task.done()]
        if not tasks:
            return

        if disconnect_message is not None:
            for stream in streams:
                stream.queue.put_nowait(disconnect_message)
            _, pending = await asyncio.wait(tasks, timeout=self.application_close_timeout)
        else:
            pending = set(tasks)

        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
