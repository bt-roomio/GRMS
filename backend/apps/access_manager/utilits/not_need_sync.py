from typing import List
from celery.utils.log import get_task_logger

from shuttle.services.publish_updates import publish_updates

logger = get_task_logger(__name__)


def not_need_sync(cards: List[str], device):
    from access_manager.models import NeedSyncDevice
    if not device:
        return

    updated_count = NeedSyncDevice.objects.filter(
        card__number__in=cards,
        device=device,
        need_sync=True
    ).update(need_sync=False)

    if updated_count > 0:
        publish_updates("need_sync", "get_list_activity", {})
        logger.info("Updated %d NeedSyncDevice objects to need_sync=False", updated_count)