import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

import asyncssh
from django.conf import settings

from fleet.exceptions import (
    FleetHostKeyMismatch,
    FleetKeyUnavailable,
    FleetNodeNotEnrolled,
    FleetNodeUnreachable,
)
from fleet.models import FleetAuditLog
from fleet.utils.audit import alog_action
from fleet.utils.db import db

logger = logging.getLogger(__name__)

# The only module that touches private keys and SSH connections.

CLOSE_TIMEOUT = 5


def _client_keys():
    path = settings.FLEET_SSH_PRIVATE_KEY_PATH
    if not path or not os.path.isfile(path):
        raise FleetKeyUnavailable(f"Fleet private key not found at {path!r}")
    return [path]


def _export(key) -> str:
    return key.export_public_key("openssh").decode().strip()


def _known_hosts_for(node):
    """
    Trust-on-first-use.

    Once pinned, asyncssh enforces the key *before* authentication, so a
    substituted host never sees our auth attempt. An unpinned node connects
    unverified once, and the key is recorded on the way out.
    """
    if not node.ssh_host_key:
        return None

    try:
        pinned = asyncssh.import_public_key(node.ssh_host_key)
    except (asyncssh.KeyImportError, ValueError) as exc:
        raise FleetHostKeyMismatch(f"Stored host key for {node.code} is unreadable: {exc}") from exc

    def resolve(host, addr, port):
        return [pinned], [], []

    return resolve


@db
def _pin_host_key(node, exported: str):
    node.ssh_host_key = exported
    node.save(update_fields=["ssh_host_key", "updated_at"])


async def _verify_or_pin(node, conn) -> None:
    key = conn.get_server_host_key()
    if key is None:
        return

    exported = _export(key)

    if node.ssh_host_key:
        # asyncssh already enforced this; belt and braces in case the pin was
        # written between building known_hosts and completing the handshake.
        if node.ssh_host_key.strip() != exported:
            raise FleetHostKeyMismatch(f"Host key changed for {node.code}")
        return

    await _pin_host_key(node, exported)
    await alog_action(
        FleetAuditLog.ACTION.HOST_KEY_PINNED,
        node=node,
        detail={"host_key": exported, "mesh_ip": node.mesh_ip},
    )


@asynccontextmanager
async def connect(node, connect_timeout=None):
    """
    Open an SSH connection to a node over the mesh.

    Key-based auth only, as `node.ssh_user` — never root, never a password.
    """
    if not node.mesh_ip:
        raise FleetNodeNotEnrolled(f"{node.code} has no mesh IP yet")

    try:
        conn = await asyncssh.connect(
            node.mesh_ip,
            port=settings.FLEET_SSH_PORT,
            username=node.ssh_user or settings.FLEET_SSH_USER,
            client_keys=_client_keys(),
            known_hosts=_known_hosts_for(node),
            connect_timeout=connect_timeout or settings.FLEET_SSH_CONNECT_TIMEOUT,
        )
    except asyncssh.HostKeyNotVerifiable as exc:
        await alog_action(
            FleetAuditLog.ACTION.HOST_KEY_MISMATCH,
            node=node,
            detail={"mesh_ip": node.mesh_ip, "error": str(exc)},
        )
        raise FleetHostKeyMismatch(
            f"Host key for {node.code} does not match the pinned key. "
            f"Refusing to connect — clear the pin only if the VM was deliberately rebuilt."
        ) from exc
    except (OSError, asyncio.TimeoutError, asyncssh.Error) as exc:
        # A bare TimeoutError stringifies to "", which reads as a blank error
        # in the UI. Fall back to the type name.
        reason = str(exc) or type(exc).__name__
        raise FleetNodeUnreachable(
            f"Cannot reach {node.code} at {node.mesh_ip}:{settings.FLEET_SSH_PORT} — {reason}"
        ) from exc

    try:
        await _verify_or_pin(node, conn)
        yield conn
    finally:
        conn.close()
        # Shielded: a browser dropping its terminal cancels the consumer task,
        # and an unshielded await here would abandon or hang the teardown.
        try:
            await asyncio.wait_for(asyncio.shield(conn.wait_closed()), timeout=CLOSE_TIMEOUT)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            logger.debug("Timed out closing SSH connection to %s", node.code)
        except Exception:  # noqa: BLE001 - teardown must never mask the real error
            logger.debug("Error while closing SSH connection to %s", node.code, exc_info=True)


async def run_command(node, command: str, timeout=None) -> dict:
    """Run one command and collect its result. Returns rc / stdout / stderr."""
    timeout = timeout or settings.FLEET_SSH_COMMAND_TIMEOUT

    async with connect(node) as conn:
        try:
            result = await asyncio.wait_for(conn.run(command, check=False), timeout=timeout)
        except asyncio.TimeoutError as exc:
            raise FleetNodeUnreachable(f"Command on {node.code} timed out after {timeout}s") from exc

    return {
        "rc": result.exit_status,
        "stdout": result.stdout or "",
        "stderr": result.stderr or "",
    }


def run_blocking(coro_factory):
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="fleet-ssh") as pool:
        return pool.submit(lambda: asyncio.run(coro_factory())).result()


def run_command_sync(node, command: str, timeout=None) -> dict:
    """Blocking wrapper for DRF views and Celery tasks."""
    return run_blocking(lambda: run_command(node, command, timeout=timeout))


async def open_pty(conn, term_type="xterm-256color", cols=80, rows=24):
    """
    Start an interactive shell.

    `encoding=None` is required: with an encoding set asyncssh decodes on the
    fly and raises when a multi-byte character is split across reads.
    """
    return await conn.create_process(
        term_type=term_type,
        term_size=(cols, rows),
        encoding=None,
    )
