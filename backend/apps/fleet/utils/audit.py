import logging

from channels.db import database_sync_to_async

from fleet.models import FleetAuditLog

logger = logging.getLogger(__name__)


def log_action(action, node=None, user=None, detail=None, remote_addr=None) -> None:
    """
    Write an audit row. Never raises — losing the trail must not take down the
    action being audited.
    """
    try:
        FleetAuditLog.objects.create(
            action=action,
            node=node,
            user=user if user and getattr(user, "is_authenticated", False) else None,
            detail=detail,
            remote_addr=remote_addr,
        )
    except Exception:
        logger.exception(
            "Failed to write fleet audit log: action=%s node=%s",
            action,
            getattr(node, "code", None),
        )


alog_action = database_sync_to_async(log_action)


def client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")
