"""The browser terminal consumer: auth, wire format, and audit."""

import json

import pytest
from asgiref.sync import sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import AnonymousUser, Permission

from fleet.models import FleetAuditLog
from fleet.tests.sshd import BANNER, fleet_settings, make_node
from shuttle.v2_consumers.fleet_terminal import CLOSE_FORBIDDEN, CLOSE_NOT_FOUND, TerminalConsumer
from users.models import User

pytestmark = pytest.mark.django_db


@sync_to_async
def make_user(node=None, with_perm=False, tenant=None):
    user = User.objects.create_user(email=f"terminal-{User.objects.count()}@example.com", password="password")
    if tenant is not None:
        user.tenant = tenant
    elif node is not None:
        user.tenant = node.tenant
    if with_perm:
        # Kept only to prove the terminal does not depend on it either way.
        user.user_permissions.add(Permission.objects.get(codename="terminal_fleetnode"))
    user.save()
    return User.objects.get(pk=user.pk)  # re-fetch so the permission cache is clean


@sync_to_async
def audit_actions(node):
    return set(FleetAuditLog.objects.filter(node=node).values_list("action", flat=True))


def build(node, user):
    communicator = WebsocketCommunicator(TerminalConsumer.as_asgi(), f"/api/ws/v2/fleet/terminal/{node.id}/")
    communicator.scope["user"] = user
    communicator.scope["url_route"] = {"kwargs": {"node_id": node.id}}
    return communicator


async def read_until(communicator, needle, tries=5):
    """
    PTY output arrives in arbitrarily sized chunks.

    Match on bare words, never on a trailing newline: a PTY translates "\\n"
    into "\\r\\n" on the way out.
    """
    buffer = b""
    for _ in range(tries):
        frame = await communicator.receive_output(timeout=5)
        if frame["type"] != "websocket.send":
            continue
        buffer += frame.get("bytes") or b""
        if needle in buffer:
            return buffer
    raise AssertionError(f"{needle!r} never arrived; got {buffer!r}")


async def refusal(communicator):
    """
    Every refusal must arrive *after* the handshake completes.

    Closing before accept never reaches the client as a close at all: the
    handshake is never completed, so Daphne answers a bare HTTP 403 and the
    close code and message are discarded. Assert the handshake succeeded, then
    read the reason and the code off the open socket.
    """
    connected, _ = await communicator.connect()
    assert connected, "refusing before accept hides the reason behind an opaque HTTP 403"

    message = json.loads((await communicator.receive_output(timeout=5))["text"])
    closed = await communicator.receive_output(timeout=5)
    return message, closed["code"]


async def test_anonymous_user_is_rejected(sshd, client_key):
    port, _ = sshd
    _, key_path = client_key
    node = await make_node()

    with fleet_settings(port, key_path):
        message, code = await refusal(build(node, AnonymousUser()))

    assert message["type"] == "error"
    assert code == CLOSE_FORBIDDEN


async def test_any_authenticated_user_of_the_tenant_may_open_a_terminal(sshd, client_key):
    """No fleet permission is required — access is gated in the UI, by decision."""
    port, _ = sshd
    _, key_path = client_key
    node = await make_node()
    user = await make_user(node, with_perm=False)

    with fleet_settings(port, key_path):
        communicator = build(node, user)
        connected, _ = await communicator.connect()
        assert connected

        await read_until(communicator, BANNER.strip().encode())
        await communicator.disconnect()


async def test_node_from_another_tenant_is_not_found(sshd, client_key):
    port, _ = sshd
    _, key_path = client_key
    node = await make_node()
    other_node = await make_node()
    user = await make_user(other_node)

    with fleet_settings(port, key_path):
        message, code = await refusal(build(node, user))

    assert message["type"] == "error"
    assert code == CLOSE_NOT_FOUND


async def test_shell_relays_bytes_in_both_directions(sshd, client_key):
    port, _ = sshd
    _, key_path = client_key
    node = await make_node()
    user = await make_user(node)

    with fleet_settings(port, key_path):
        communicator = build(node, user)
        connected, _ = await communicator.connect()
        assert connected

        await read_until(communicator, BANNER.strip().encode())

        await communicator.send_to(bytes_data=b"echo me\n")
        echoed = await read_until(communicator, b"echo me")
        assert isinstance(echoed, bytes), "PTY traffic must stay in binary frames"

        await communicator.disconnect()

    assert await audit_actions(node) >= {
        FleetAuditLog.ACTION.TERMINAL_OPEN,
        FleetAuditLog.ACTION.TERMINAL_CLOSE,
    }


async def test_resize_control_message_is_not_typed_into_the_shell(sshd, client_key):
    port, _ = sshd
    _, key_path = client_key
    node = await make_node()
    user = await make_user(node)

    with fleet_settings(port, key_path):
        communicator = build(node, user)
        await communicator.connect()
        await read_until(communicator, BANNER.strip().encode())

        await communicator.send_to(text_data=json.dumps({"type": "resize", "cols": 120, "rows": 40}))
        await communicator.send_to(bytes_data=b"after resize\n")

        echoed = await read_until(communicator, b"after resize")
        assert b"resize" not in echoed.replace(b"after resize", b""), "control JSON must never reach stdin"

        await communicator.disconnect()


async def test_unreachable_node_closes_with_an_error(client_key):
    _, key_path = client_key
    node = await make_node(mesh_ip="127.0.0.1")
    user = await make_user(node)

    # Port 1 has nothing listening on it.
    with fleet_settings(1, key_path, FLEET_SSH_CONNECT_TIMEOUT=2):
        communicator = build(node, user)
        connected, _ = await communicator.connect()
        assert connected

        message = json.loads((await communicator.receive_output(timeout=10))["text"])
        assert message["type"] == "error"

        await communicator.disconnect()
