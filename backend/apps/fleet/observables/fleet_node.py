import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction

logger = logging.getLogger(__name__)


def _send(tenant_ids) -> None:
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return

    for tenant_id in tenant_ids:
        try:
            async_to_sync(channel_layer.group_send)(
                f"fleet_nodes_{tenant_id}",
                {"type": "fleet.node.update"},
            )
        except Exception:
            logger.exception("Failed to push fleet update for tenant %s", tenant_id)


def publish_fleet_nodes(tenant_ids) -> None:
    tenant_ids = {tenant_id for tenant_id in tenant_ids if tenant_id}
    if not tenant_ids:
        return

    transaction.on_commit(lambda: _send(tenant_ids))
