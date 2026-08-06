"""
A real in-process SSH server for the fleet tests.

Mocking asyncssh would prove little: these tests exist to establish that its
host-key verification and PTY handling behave the way the fleet code assumes.
"""

import asyncssh
import pytest
from django.test import override_settings

from fleet.tests.factories import SSH_USER, create_gateway, create_node, make_node  # noqa: F401

BANNER = "welcome\n"


async def handle_process(process):
    """Exec requests report back; a bare shell echoes, like a real terminal."""
    command = process.command

    if command == "fail":
        process.stderr.write("nope\n")
        process.exit(3)
        return

    if command:
        process.stdout.write(f"ran:{command}\n")
        process.exit(0)
        return

    process.stdout.write(BANNER)
    while True:
        try:
            data = await process.stdin.readline()
        except asyncssh.TerminalSizeChanged:
            # asyncssh surfaces a window-change request by raising here. A real
            # shell absorbs it and keeps reading, so the fake one must too.
            continue
        except Exception:  # noqa: BLE001 - the client hanging up is normal here
            break

        if not data or data.strip() == "exit":
            break
        process.stdout.write(data)

    process.exit(0)


@pytest.fixture
def upload_root(tmp_path):
    root = tmp_path / "opt" / "roomio"
    root.mkdir(parents=True)
    return root


@pytest.fixture
def client_key(tmp_path):
    """Stands in for the fleet private key held by the Django server."""
    key = asyncssh.generate_private_key("ssh-ed25519")
    path = tmp_path / "fleet_key"
    path.write_bytes(key.export_private_key())
    return key, str(path)


@pytest.fixture
async def sshd(client_key):
    key, _ = client_key
    host_key = asyncssh.generate_private_key("ssh-ed25519")

    server = await asyncssh.create_server(
        lambda: asyncssh.SSHServer(),
        "127.0.0.1",
        0,
        server_host_keys=[host_key],
        authorized_client_keys=asyncssh.import_authorized_keys(key.export_public_key().decode()),
        process_factory=handle_process,
        sftp_factory=True,
    )
    port = server.sockets[0].getsockname()[1]
    try:
        yield port, host_key
    finally:
        server.close()
        await server.wait_closed()


def fleet_settings(port, key_path, **extra):
    values = {
        "FLEET_SSH_PORT": port,
        "FLEET_SSH_PRIVATE_KEY_PATH": key_path,
        "FLEET_SSH_USER": SSH_USER,
        "FLEET_SSH_CONNECT_TIMEOUT": 5,
        "FLEET_SSH_COMMAND_TIMEOUT": 10,
    }
    values.update(extra)
    return override_settings(**values)
