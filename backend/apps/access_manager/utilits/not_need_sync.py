from functools import partial
from typing import List

from celery.utils.log import get_task_logger
from django.db import transaction

from shuttle.services.publish_updates import publish_updates

logger = get_task_logger(__name__)


def not_need_sync(cards: List[str], devices):
    from access_manager.models import NeedSyncDevice

    if not devices:
        return

    updated_count = NeedSyncDevice.objects.filter(
        card__number__in=cards, device__in=list(devices), need_sync=True
    ).update(need_sync=False)

    if updated_count > 0:
        for tenant_id in {device.tenant_id for device in devices}:
            transaction.on_commit(partial(publish_updates, f"need_sync_{tenant_id}", "get_list_activity", {}))
        logger.info("Updated %d NeedSyncDevice objects to need_sync=False", updated_count)
