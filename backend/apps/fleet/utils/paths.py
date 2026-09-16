import posixpath

from django.conf import settings


def ssh_user(node) -> str:
    return node.ssh_user or settings.FLEET_SSH_USER


def ssh_home(node) -> str:
    return f"/home/{ssh_user(node)}"


def upload_root(node) -> str:
    configured = (settings.FLEET_UPLOAD_ROOT or "").strip()
    return posixpath.normpath(configured or ssh_home(node)).rstrip("/") or "/"
