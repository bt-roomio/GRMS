import asyncio
import json
import logging
from contextlib import AsyncExitStack

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from core.utils.get_time import get_mil_sec
from fleet.models import FleetAuditLog, FleetNode
from fleet.utils import ssh
from fleet.utils.audit import alog_action
from fleet.utils.exceptions import FleetError, FleetHostKeyMismatch
from fleet.utils.scope import tenant_scope_for_user

logger = logging.getLogger(__name__)

# Close codes above 4000 are ours. The frontend maps them to a message.
CLOSE_FORBIDDEN = 4403
CLOSE_NOT_FOUND = 4404
CLOSE_UNREACHABLE = 4503
CLOSE_HOST_KEY = 4526
CLOSE_SERVER_ERROR = 4500

TEARDOWN_TIMEOUT = 5
READ_SIZE = 8192
MAX_COLS = 500
MAX_ROWS = 300


class TerminalConsumer(AsyncWebsocketConsumer):
    """
    Interactive shell on one fleet node.

    Wire format: **binary** frames carry raw PTY bytes both ways, **text**
    frames carry JSON control messages (resize, and errors on the way back).
    Nothing is base64-encoded.

    Open to any authenticated user by decision — access is gated in the UI.
    Tenant scoping is not part of that and is still enforced below.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.node = None
        self.process = None
        self.stack = None
        self.pumps = []
        self.opened_at = None

    # -- lifecycle ---------------------------------------------------------

    async def connect(self):
        node_id = self.scope["url_route"]["kwargs"]["node_id"]
        user = self.scope.get("user")

        # Accept first, then decide. A close sent before accept never reaches
        # the client as a close: Daphne turns it into a bare HTTP 403 and the
        # code and message are discarded, leaving the caller nothing to act on.
        await self.accept()

        if user is None or not user.is_authenticated:
            await self.fail("Not authenticated.", CLOSE_FORBIDDEN)
            return

        self.node = await self.get_node(user, node_id)
        if self.node is None:
            await self.fail("Node not found.", CLOSE_NOT_FOUND)
            return

        try:
            await self.start_session()
        except FleetHostKeyMismatch as exc:
            await alog_action(
                FleetAuditLog.ACTION.TERMINAL_DENIED,
                node=self.node,
                user=user,
                detail={"reason": "host key mismatch"},
            )
            await self.fail(str(exc), CLOSE_HOST_KEY)
            return
        except FleetError as exc:
            await self.fail(str(exc), CLOSE_UNREACHABLE)
            return
        except Exception:
            logger.exception("Terminal session failed to start for %s", self.node.code)
            await self.fail("Could not open a shell on this node.", CLOSE_SERVER_ERROR)
            return

        self.opened_at = get_mil_sec()
        await alog_action(
            FleetAuditLog.ACTION.TERMINAL_OPEN,
            node=self.node,
            user=user,
            detail={"mesh_ip": self.node.mesh_ip, "ssh_user": self.node.ssh_user},
        )

    async def start_session(self):
        """Open the SSH connection and PTY, and start pumping both directions."""
        self.stack = AsyncExitStack()
        conn = await self.stack.enter_async_context(ssh.connect(self.node))
        self.process = await ssh.open_pty(conn)

        self.pumps = [
            asyncio.create_task(self.pump(self.process.stdout)),
            asyncio.create_task(self.pump(self.process.stderr)),
            asyncio.create_task(self.watch_exit()),
        ]

    async def disconnect(self, code):
        """
        Tear the session down.

        A vanishing browser gets here via task cancellation, so every await is
        bounded and shielded: a hung remote must not keep the SSH connection
        alive forever.
        """
        for task in self.pumps:
            task.cancel()
        self.pumps = []

        if self.process is not None:
            try:
                self.process.close()
            except Exception:
                logger.debug("Error closing PTY", exc_info=True)
            self.process = None

        if self.stack is not None:
            await self.guarded(self.stack.aclose(), "closing the SSH connection")
            self.stack = None

        if self.node is not None and self.opened_at is not None:
            await self.guarded(
                alog_action(
                    FleetAuditLog.ACTION.TERMINAL_CLOSE,
                    node=self.node,
                    user=self.scope.get("user"),
                    detail={
                        "duration_ms": get_mil_sec() - self.opened_at,
                        "close_code": code,
                    },
                ),
                "writing the close audit entry",
            )
            self.opened_at = None

    async def guarded(self, coro, what):
        try:
            await asyncio.wait_for(asyncio.shield(coro), timeout=TEARDOWN_TIMEOUT)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            logger.warning("Terminal teardown timed out while %s", what)
        except Exception:
            logger.debug("Terminal teardown failed while %s", what, exc_info=True)

    # -- browser -> node ---------------------------------------------------

    async def receive(self, text_data=None, bytes_data=None):
        if bytes_data is not None:
            await self.write(bytes_data)
            return

        if not text_data:
            return

        try:
            message = json.loads(text_data)
        except json.JSONDecodeError:
            # Text frames are control-only; keystrokes are binary. Drop rather
            # than inject into the shell.
            logger.debug("Dropping non-JSON text frame on terminal socket")
            return

        if message.get("type") == "resize":
            await self.resize(message)

    async def write(self, data: bytes):
        if self.process is None:
            return
        try:
            self.process.stdin.write(data)
        except (BrokenPipeError, ConnectionResetError):
            await self.close(code=CLOSE_UNREACHABLE)

    async def resize(self, message):
        if self.process is None:
            return
        try:
            cols = max(1, min(int(message.get("cols", 80)), MAX_COLS))
            rows = max(1, min(int(message.get("rows", 24)), MAX_ROWS))
        except (TypeError, ValueError):
            return

        try:
            self.process.change_terminal_size(cols, rows)
        except Exception:
            logger.debug("Terminal resize failed", exc_info=True)

    # -- node -> browser ---------------------------------------------------

    async def pump(self, reader):
        """Relay one PTY stream to the browser until it closes."""
        try:
            while True:
                chunk = await reader.read(READ_SIZE)
                if not chunk:
                    break
                await self.send(bytes_data=chunk)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.debug("Terminal stream ended", exc_info=True)

    async def watch_exit(self):
        """Close the socket once the remote shell itself exits."""
        try:
            await self.process.wait_closed()
            status = self.process.exit_status
        except asyncio.CancelledError:
            raise
        except Exception:
            status = None

        try:
            await self.send(text_data=json.dumps({"type": "exit", "status": status}))
        except Exception:
            logger.debug("Could not report shell exit", exc_info=True)

        await self.close()

    # -- helpers -----------------------------------------------------------

    async def fail(self, message, code):
        try:
            await self.send(text_data=json.dumps({"type": "error", "message": message}))
        except Exception:
            logger.debug("Could not deliver terminal error", exc_info=True)
        await self.close(code=code)

    @database_sync_to_async
    def get_node(self, user, node_id):
        return FleetNode.objects.is_active().for_tenant(tenant_scope_for_user(user)).filter(pk=node_id).first()
