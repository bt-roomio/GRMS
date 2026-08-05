import asyncio
import hashlib
import logging
import posixpath
import uuid

import asyncssh
from django.conf import settings

from fleet.exceptions import FleetPathRejected, FleetTransferFailed
from fleet.ssh import connect, run_blocking
from fleet.utils.paths import ssh_user, upload_root

logger = logging.getLogger(__name__)


CHUNK_SIZE = 256 * 1024
TMP_SUFFIX = ".roomio-part"


def _is_under(path: str, root: str) -> bool:
    return path == root or path.startswith(root.rstrip("/") + "/")


def safe_filename(name: str) -> str:
    """
    Reduce an uploaded file's name to a bare filename.

    Only the basename survives, so a client sending `../../etc/passwd` or a
    Windows path uploads a file *called* `passwd` into the root instead of
    escaping it. Browsers already send a basename; this is for everyone else.
    """
    raw = posixpath.basename((name or "").strip().replace("\\", "/")).strip()

    if not raw or raw in (".", "..") or "\x00" in raw:
        raise FleetPathRejected("The file has no usable name.")

    return raw


def resolve_dest(root: str, filename: str) -> str:
    """
    Place a file directly in the node's upload root — the directory the browser
    terminal opens in.

    `safe_filename` has already stripped any directory part; `normpath` and the
    containment check stay as a second pair of eyes, and `_realpath_guard` does
    the matching check against symlinks on the node itself.
    """
    resolved = posixpath.normpath(posixpath.join(root, safe_filename(filename)))

    if not _is_under(resolved, root) or resolved == root:
        raise FleetPathRejected(f"Destination must be a file inside {root}.")

    return resolved


def _is_dir(attrs) -> bool:
    return ((attrs.permissions or 0) & 0o170000) == 0o040000


def _is_link(attrs) -> bool:
    return ((attrs.permissions or 0) & 0o170000) == 0o120000


async def _real(sftp, path: str) -> str:
    return (await sftp.realpath(path)).rstrip("/") or "/"


async def _resolved_root(sftp, node) -> str:
    """
    Where the upload root really lives on the node.

    Unconfigured it is the agent's home, which is also where the browser
    terminal opens — `bootstrap.sh` creates the account with that home and
    installs authorized_keys inside it, so the two cannot drift apart on a node
    this system enrolled.

    Every later check compares against the node's own answer rather than the
    string we sent, so a root reached through a symlink still matches its own
    children instead of rejecting all of them.
    """
    root = upload_root(node)
    try:
        return await _real(sftp, root)
    except asyncssh.SFTPError as exc:
        raise FleetTransferFailed(f"Upload root {root} is not usable on the node: {exc}") from exc


async def _realpath_guard(sftp, path: str, real_root: str) -> None:
    """
    Ask the node where a path really points.

    The textual check in `resolve_dest` cannot see a symlink sitting inside the
    root, so the node gets the final word before anything is written.
    """
    try:
        real = await _real(sftp, path)
    except asyncssh.SFTPError as exc:
        raise FleetTransferFailed(f"Cannot resolve {path} on the node: {exc}") from exc

    if not _is_under(real, real_root):
        raise FleetPathRejected(f"{path} resolves to {real} on the node, which is outside {real_root}.")


async def _require_directory(sftp, real_root: str) -> None:
    """Every upload lands straight in the root, so it has to be a real directory."""
    try:
        attrs = await sftp.stat(real_root)
    except asyncssh.SFTPNoSuchFile as exc:
        raise FleetTransferFailed(f"Upload root {real_root} does not exist on the node.") from exc
    except asyncssh.SFTPError as exc:
        raise FleetTransferFailed(f"Cannot stat {real_root} on the node: {exc}") from exc

    if not _is_dir(attrs):
        raise FleetTransferFailed(f"Upload root {real_root} is not a directory on the node.")


async def _check_target(sftp, dest: str, root: str, overwrite: bool) -> bool:
    """Returns whether the destination already exists. Refuses unsafe targets."""
    try:
        # lstat, not stat: a symlink must be seen as a symlink, not followed.
        attrs = await sftp.lstat(dest)
    except asyncssh.SFTPNoSuchFile:
        return False
    except asyncssh.SFTPError as exc:
        raise FleetTransferFailed(f"Cannot stat {dest} on the node: {exc}") from exc

    if not overwrite:
        raise FleetTransferFailed(f"{dest} already exists on the node. Pass overwrite=true to replace it.")

    if _is_dir(attrs):
        raise FleetPathRejected(f"{dest} is a directory on the node.")
    if _is_link(attrs):
        raise FleetPathRejected(f"{dest} is a symlink on the node. Refusing to write through it.")

    await _realpath_guard(sftp, dest, root)
    return True


async def _stream(sftp, node, fileobj, tmp_path: str, max_bytes: int) -> tuple[int, str]:
    digest = hashlib.sha256()
    written = 0

    try:
        async with sftp.open(tmp_path, "wb") as remote:
            for chunk in iter(lambda: fileobj.read(CHUNK_SIZE), b""):
                written += len(chunk)
                if written > max_bytes:
                    raise FleetTransferFailed(f"File exceeds the {max_bytes} byte upload limit.")
                digest.update(chunk)
                await remote.write(chunk)
    except asyncssh.SFTPPermissionDenied as exc:
        # Nothing we can fix from here — the account cannot write where it lands.
        raise FleetTransferFailed(
            f"{ssh_user(node)} is not allowed to write in {posixpath.dirname(tmp_path)} on {node.code}. "
            f"Check the directory's owner and mode on the node."
        ) from exc
    except asyncssh.SFTPError as exc:
        raise FleetTransferFailed(f"Writing to {node.code} failed: {exc}") from exc

    return written, digest.hexdigest()


async def _commit(sftp, tmp_path: str, dest: str, mode: int | None) -> None:
    """Move the finished temp file into place, atomically where the node allows."""
    if mode is not None:
        try:
            await sftp.chmod(tmp_path, mode)
        except asyncssh.SFTPError as exc:
            raise FleetTransferFailed(f"Cannot set mode on {tmp_path}: {exc}") from exc

    try:
        # posix_rename replaces the target in one step. Servers without the
        # extension need the target gone first, which briefly leaves a gap.
        await sftp.posix_rename(tmp_path, dest)
    except asyncssh.SFTPError:
        try:
            await sftp.remove(dest)
        except asyncssh.SFTPError:
            pass
        try:
            await sftp.rename(tmp_path, dest)
        except asyncssh.SFTPError as exc:
            raise FleetTransferFailed(f"Cannot move the upload into place at {dest}: {exc}") from exc


async def _cleanup(sftp, tmp_path: str) -> None:
    try:
        await sftp.remove(tmp_path)
    except Exception:
        logger.debug("Could not remove temp upload %s", tmp_path, exc_info=True)


async def upload(node, fileobj, filename: str, mode: int | None = None, overwrite: bool = True) -> dict:
    """
    Send one file to a node, into the upload root under its own name.

    Written to `<dest>.roomio-part` first and renamed on success, so a dropped
    connection never leaves a half-written file under the real name.
    """
    # Fail on an unusable name before spending a connection on it.
    safe_filename(filename)
    max_bytes = settings.FLEET_UPLOAD_MAX_BYTES

    async with connect(node) as conn:
        async with conn.start_sftp_client() as sftp:
            real_root = await _resolved_root(sftp, node)
            await _require_directory(sftp, real_root)

            dest = resolve_dest(real_root, filename)
            tmp_path = f"{dest}{TMP_SUFFIX}-{uuid.uuid4().hex[:8]}"
            replaced = await _check_target(sftp, dest, real_root, overwrite)

            try:
                size, checksum = await _stream(sftp, node, fileobj, tmp_path, max_bytes)
            except Exception:
                await _cleanup(sftp, tmp_path)
                raise

            try:
                await _commit(sftp, tmp_path, dest, mode)
            except Exception:
                await _cleanup(sftp, tmp_path)
                raise

    return {
        "path": dest,
        "size": size,
        "sha256": checksum,
        "mode": f"{mode:04o}" if mode is not None else None,
        "replaced": replaced,
    }


async def _upload_with_timeout(node, fileobj, filename, mode, overwrite, timeout):
    try:
        return await asyncio.wait_for(
            upload(node, fileobj, filename, mode=mode, overwrite=overwrite),
            timeout=timeout,
        )
    except asyncio.TimeoutError as exc:
        raise FleetTransferFailed(f"Upload to {node.code} timed out after {timeout}s") from exc


def upload_sync(node, fileobj, filename: str, mode=None, overwrite: bool = True, timeout=None) -> dict:
    """Blocking wrapper for DRF views and Celery tasks."""
    timeout = timeout or settings.FLEET_UPLOAD_TIMEOUT
    return run_blocking(lambda: _upload_with_timeout(node, fileobj, filename, mode, overwrite, timeout))
