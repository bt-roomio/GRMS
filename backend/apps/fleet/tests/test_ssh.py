"""TOFU host-key handling and command execution, against a real SSH server."""

import asyncssh
import pytest
from asgiref.sync import sync_to_async

from fleet.models import FleetAuditLog
from fleet.tests.sshd import fleet_settings, make_node
from fleet.utils import ssh
from fleet.utils.exceptions import FleetHostKeyMismatch, FleetKeyUnavailable, FleetNodeNotEnrolled

pytestmark = pytest.mark.django_db


@sync_to_async
def has_audit(node, action):
    return FleetAuditLog.objects.filter(node=node, action=action).exists()


async def test_first_connect_pins_the_host_key(sshd, client_key):
    port, host_key = sshd
    _, key_path = client_key
    node = await make_node()

    with fleet_settings(port, key_path):
        result = await ssh.run_command(node, "uptime")

    assert result["rc"] == 0
    assert "ran:uptime" in result["stdout"]

    await sync_to_async(node.refresh_from_db)()
    assert node.ssh_host_key == host_key.export_public_key("openssh").decode().strip()
    assert await has_audit(node, FleetAuditLog.ACTION.HOST_KEY_PINNED)


async def test_pinned_key_is_reused_on_later_connections(sshd, client_key):
    port, _ = sshd
    _, key_path = client_key
    node = await make_node()

    with fleet_settings(port, key_path):
        await ssh.run_command(node, "first")
        pinned_after_first = node.ssh_host_key
        result = await ssh.run_command(node, "second")

    assert result["rc"] == 0
    await sync_to_async(node.refresh_from_db)()
    assert node.ssh_host_key == pinned_after_first


async def test_a_substituted_host_key_is_refused(sshd, client_key):
    port, _ = sshd
    _, key_path = client_key
    node = await make_node()

    # Pin someone else's key: this is what a swapped-out host looks like.
    impostor = asyncssh.generate_private_key("ssh-ed25519")
    node.ssh_host_key = impostor.export_public_key("openssh").decode().strip()
    await sync_to_async(node.save)()

    with fleet_settings(port, key_path):
        with pytest.raises(FleetHostKeyMismatch):
            await ssh.run_command(node, "uptime")

    assert await has_audit(node, FleetAuditLog.ACTION.HOST_KEY_MISMATCH)

    await sync_to_async(node.refresh_from_db)()
    assert (
        node.ssh_host_key == impostor.export_public_key("openssh").decode().strip()
    ), "a mismatch must never silently re-pin"


async def test_non_zero_exit_is_reported_not_raised(sshd, client_key):
    port, _ = sshd
    _, key_path = client_key
    node = await make_node()

    with fleet_settings(port, key_path):
        result = await ssh.run_command(node, "fail")

    assert result["rc"] == 3
    assert "nope" in result["stderr"]


async def test_pty_streams_raw_bytes(sshd, client_key):
    port, _ = sshd
    _, key_path = client_key
    node = await make_node()

    with fleet_settings(port, key_path):
        async with ssh.connect(node) as conn:
            process = await ssh.open_pty(conn, cols=100, rows=30)
            chunk = await process.stdout.read(1024)
            process.close()

    assert isinstance(chunk, bytes), "encoding=None keeps the PTY a byte pipe"


async def test_unenrolled_node_is_rejected_before_dialling(client_key):
    _, key_path = client_key
    node = await make_node()
    node.mesh_ip = None

    with fleet_settings(22, key_path):
        with pytest.raises(FleetNodeNotEnrolled):
            await ssh.run_command(node, "uptime")


async def test_missing_private_key_is_reported_clearly(sshd, tmp_path):
    port, _ = sshd
    node = await make_node()

    with fleet_settings(port, str(tmp_path / "absent_key")):
        with pytest.raises(FleetKeyUnavailable):
            await ssh.run_command(node, "uptime")
