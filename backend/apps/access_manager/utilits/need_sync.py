from typing import List
from celery.utils.log import get_task_logger

from shuttle.services.publish_updates import publish_updates

logger = get_task_logger(__name__)


def need_sync(cards: List[str], device, access, user=None, reason=""):
    from access_manager.models import Card, NeedSyncDevice

    if not device:
        return

    for card_num in cards:
        try:
            card = Card.objects.get(number=card_num, tenant=device.tenant)

            message_params = {"access": access, "reason": reason}

            sync_obj, created = NeedSyncDevice.objects.get_or_create(
                card=card,
                device=device,
                defaults={
                    "need_sync": True,
                    "additional_info": {"message_params": message_params},
                    "created_by_id": user,
                    "updated_by_id": user,
                },
            )
            if created:
                publish_updates("need_sync", "get_list_activity", {})
            else:
                info = sync_obj.additional_info or {}
                info["message_params"] = message_params

                sync_obj.need_sync = True
                sync_obj.updated_by_id = user
                sync_obj.additional_info = info
                sync_obj.save()
                publish_updates("need_sync", "get_list_activity", {})

        except Card.DoesNotExist:
            logger.error("Card '%s' not found, skipping sync", card_num)
        except Exception as e:
            logger.error("Failed to update NeedSyncDevice for card '%s': '%s'", card_num, str(e))
