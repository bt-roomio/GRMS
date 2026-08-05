"""File uploads over SFTP, against a real SSH server and a real directory tree."""

import hashlib
import io

import asyncssh
import pytest
from asgiref.sync import sync_to_async
from django.test import override_settings

from fleet import sftp
from fleet.exceptions import (
    FleetHostKeyMismatch,
    FleetNodeNotEnrolled,
    FleetPathRejected,
    FleetTransferFailed,
)
from fleet.models import FleetNode
from fleet.tests.sshd import fleet_settings, make_node

pytestmark = pytest.mark.django_db

CONTENT = b"roomio config\n"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def upload_settings(port, key_path, root, **extra):
    return fleet_settings(port, key_path, FLEET_UPLOAD_ROOT=str(root), **extra)


# --- picking the root and the filename, no real server involved ---------------

# Unsaved: only `ssh_user` is ever read off it.
BARE_NODE = FleetNode(ssh_user="roomio-agent")

HOME = "/home/roomio-agent"


class FakeSFTP:
    """Records what `_resolved_root` asks the node for."""

    def __init__(self, answer=HOME):
        self.answer = answer
        self.asked = None

    async def realpath(self, path):
        self.asked = path
        return self.answer


@override_settings(FLEET_UPLOAD_ROOT="")
async def test_an_unset_root_is_the_agents_home():
    """
    Safe to derive rather than ask, because `bootstrap.sh` is what creates the
    account: `useradd -m -d /home/<user>` makes the home exactly this, and the
    authorized_keys it writes there is what SSH authenticates against — a node
    whose home were anywhere else could not be logged into in the first place.
    """
    fake = FakeSFTP()

    assert await sftp._resolved_root(fake, BARE_NODE) == HOME
    assert fake.asked == HOME


@override_settings(FLEET_UPLOAD_ROOT="")
async def test_an_unset_root_follows_the_nodes_own_ssh_user():
    fake = FakeSFTP(answer="/home/other-agent")

    assert await sftp._resolved_root(fake, FleetNode(ssh_user="other-agent")) == "/home/other-agent"
    assert fake.asked == "/home/other-agent"


@override_settings(FLEET_UPLOAD_ROOT="/opt/roomio")
async def test_a_configured_root_overrides_the_home_directory():
    fake = FakeSFTP(answer="/opt/roomio")

    assert await sftp._resolved_root(fake, BARE_NODE) == "/opt/roomio"
    assert fake.asked == "/opt/roomio"


@override_settings(FLEET_UPLOAD_ROOT="")
async def test_the_root_is_taken_as_the_node_resolves_it():
    """A home reached through a symlink still has to match its own children."""
    fake = FakeSFTP(answer="/mnt/data/roomio-agent")

    assert await sftp._resolved_root(fake, BARE_NODE) == "/mnt/data/roomio-agent"


@pytest.mark.parametrize(
    "given,expected",
    [
        # A directory part is dropped, never followed.
        ("../../etc/passwd", f"{HOME}/passwd"),
        ("/etc/shadow", f"{HOME}/shadow"),
        ("conf/../../../etc/passwd", f"{HOME}/passwd"),
        (r"C:\Users\me\app.yml", f"{HOME}/app.yml"),
        ("nested/app.yml", f"{HOME}/app.yml"),
        ("  app.yml  ", f"{HOME}/app.yml"),
        # A leading dot is a legitimate filename, not a traversal.
        (".env", f"{HOME}/.env"),
    ],
)
def test_only_the_filename_survives(given, expected):
    assert sftp.resolve_dest(HOME, given) == expected


@pytest.mark.parametrize("given", ["", "   ", "/", "..", ".", "../", "app\x00.yml"])
def test_a_file_with_no_usable_name_is_refused(given):
    with pytest.raises(FleetPathRejected):
        sftp.resolve_dest(HOME, given)


# --- upload: end to end over the test SSH server -----------------------------


async def test_upload_writes_the_file_and_reports_its_hash(sshd, client_key, upload_root):
    port, _ = sshd
    _, key_path = client_key
    node = await make_node()

    with upload_settings(port, key_path, upload_root):
        result = await sftp.upload(node, io.BytesIO(CONTENT), "app.yml", mode=0o644)

    written = upload_root / "app.yml"
    assert written.read_bytes() == CONTENT
    assert result == {
        "path": str(written),
        "size": len(CONTENT),
        "sha256": sha(CONTENT),
        "mode": "0644",
        "replaced": False,
    }
    assert (written.stat().st_mode & 0o777) == 0o644


async def test_any_file_type_goes_through_byte_for_byte(sshd, client_key, upload_root):
    """
    No allowlist and no text handling anywhere — .docx, .json, .zip, an image,
    all of it is just bytes. Content here is deliberately not valid UTF-8.
    """
    blob = bytes(range(256)) * 40

    port, _ = sshd
    _, key_path = client_key
    node = await make_node()

    with upload_settings(port, key_path, upload_root):
        result = await sftp.upload(node, io.BytesIO(blob), "report.docx")

    assert (upload_root / "report.docx").read_bytes() == blob
    assert result["sha256"] == sha(blob)
    assert result["size"] == len(blob)


async def test_a_nested_filename_lands_flat_in_the_root(sshd, client_key, upload_root):
    port, _ = sshd
    _, key_path = client_key
    node = await make_node()

    with upload_settings(port, key_path, upload_root):
        result = await sftp.upload(node, io.BytesIO(CONTENT), "../../etc/passwd")

    assert (upload_root / "passwd").read_bytes() == CONTENT
    assert result["path"] == str(upload_root / "passwd")


async def test_a_same_named_file_is_replaced_by_default(sshd, client_key, upload_root):
    port, _ = sshd
    _, key_path = client_key
    node = await make_node()

    target = upload_root / "app.yml"
    target.write_bytes(b"original\n")

    with upload_settings(port, key_path, upload_root):
        result = await sftp.upload(node, io.BytesIO(CONTENT), "app.yml")

    assert target.read_bytes() == CONTENT
    assert result["replaced"] is True


async def test_overwrite_off_keeps_the_existing_file(sshd, client_key, upload_root):
    port, _ = sshd
    _, key_path = client_key
    node = await make_node()

    target = upload_root / "app.yml"
    target.write_bytes(b"original\n")

    with upload_settings(port, key_path, upload_root):
        with pytest.raises(FleetTransferFailed, match="already exists"):
            await sftp.upload(node, io.BytesIO(CONTENT), "app.yml", overwrite=False)

    assert target.read_bytes() == b"original\n"


async def test_a_symlink_pointing_outside_the_root_is_refused(sshd, client_key, upload_root, tmp_path):
    port, _ = sshd
    _, key_path = client_key
    node = await make_node()

    outside = tmp_path / "outside.yml"
    outside.write_bytes(b"do not touch\n")
    (upload_root / "app.yml").symlink_to(outside)

    with upload_settings(port, key_path, upload_root):
        with pytest.raises(FleetPathRejected, match="symlink"):
            await sftp.upload(node, io.BytesIO(CONTENT), "app.yml")

    assert outside.read_bytes() == b"do not touch\n"


async def test_writing_over_a_directory_is_refused(sshd, client_key, upload_root):
    port, _ = sshd
    _, key_path = client_key
    node = await make_node()

    (upload_root / "conf").mkdir()

    with upload_settings(port, key_path, upload_root):
        with pytest.raises(FleetPathRejected, match="directory"):
            await sftp.upload(node, io.BytesIO(CONTENT), "conf")


async def test_a_root_the_agent_cannot_write_to_says_so_plainly(sshd, client_key, upload_root):
    """
    What a real node does when the directory is not the agent's to write in.
    asyncssh raises SFTPPermissionDenied, which reached the client as a 500
    until it was folded into FleetTransferFailed.
    """
    port, _ = sshd
    _, key_path = client_key
    node = await make_node()
    upload_root.chmod(0o500)

    try:
        with upload_settings(port, key_path, upload_root):
            with pytest.raises(FleetTransferFailed, match="not allowed to write"):
                await sftp.upload(node, io.BytesIO(CONTENT), "app.yml")
    finally:
        upload_root.chmod(0o700)


async def test_a_missing_upload_root_is_refused(sshd, client_key, upload_root):
    port, _ = sshd
    _, key_path = client_key
    node = await make_node()

    with upload_settings(port, key_path, upload_root / "does-not-exist"):
        with pytest.raises(FleetTransferFailed, match="does not exist"):
            await sftp.upload(node, io.BytesIO(CONTENT), "app.yml")


async def test_a_file_over_the_size_limit_leaves_nothing_behind(sshd, client_key, upload_root):
    port, _ = sshd
    _, key_path = client_key
    node = await make_node()

    with upload_settings(port, key_path, upload_root, FLEET_UPLOAD_MAX_BYTES=4):
        with pytest.raises(FleetTransferFailed, match="upload limit"):
            await sftp.upload(node, io.BytesIO(b"x" * 64), "big.bin")

    # Neither the destination nor the staging file survives a rejected transfer.
    assert list(upload_root.iterdir()) == []


async def test_a_mismatched_host_key_blocks_the_upload(sshd, client_key, upload_root):
    port, _ = sshd
    _, key_path = client_key
    node = await make_node()

    impostor = asyncssh.generate_private_key("ssh-ed25519")
    node.ssh_host_key = impostor.export_public_key("openssh").decode().strip()
    await sync_to_async(node.save)()

    with upload_settings(port, key_path, upload_root):
        with pytest.raises(FleetHostKeyMismatch):
            await sftp.upload(node, io.BytesIO(CONTENT), "app.yml")

    assert list(upload_root.iterdir()) == []


async def test_upload_sync_survives_being_called_from_an_asgi_worker(sshd, client_key, upload_root):
    """
    Under ASGI, Django runs a sync view through `sync_to_async`, which leaves a
    CurrentThreadExecutor bound to the view's thread. The host-key pin inside is
    a nested `database_sync_to_async`, so running the coroutine on that same
    thread raises "You cannot submit onto CurrentThreadExecutor from its own
    thread". This is that arrangement, with an unpinned node so the pin runs.
    """
    port, host_key = sshd
    _, key_path = client_key
    node = await make_node()
    assert not node.ssh_host_key

    with upload_settings(port, key_path, upload_root):
        result = await sync_to_async(sftp.upload_sync)(node, io.BytesIO(CONTENT), "app.yml")

    assert (upload_root / "app.yml").read_bytes() == CONTENT
    assert result["sha256"] == sha(CONTENT)

    await sync_to_async(node.refresh_from_db)()
    assert node.ssh_host_key == host_key.export_public_key("openssh").decode().strip()


async def test_an_unenrolled_node_is_refused_before_connecting(upload_root):
    node = await make_node(mesh_ip=None)

    with override_settings(FLEET_UPLOAD_ROOT=str(upload_root)):
        with pytest.raises(FleetNodeNotEnrolled):
            await sftp.upload(node, io.BytesIO(CONTENT), "app.yml")
