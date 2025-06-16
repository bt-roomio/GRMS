from typing import List
from celery.utils.log import get_task_logger

from access_manager.utilits.batch_cards import is_same_request
from shuttle.services.publish_updates import publish_updates

logger = get_task_logger(__name__)


def need_sync(cards: List[str], device, message: dict):
    from access_manager.models import Card, NeedSyncDevice
    if not device:
        return

    original_params = message.get("data", {}).get("data", {}).get("params", [])

    for card_num in cards:
        try:
            card = Card.objects.get(number=card_num)
            single_card_param = next((param for param in original_params if param.get("cardNumber") == card_num), None)
            if not single_card_param:
                continue

            single_card_message = {
                **message,
                "data": {
                    **message["data"],
                    "data": {
                        **message["data"]["data"],
                        "params": [single_card_param],
                    },
                },
            }

            sync_obj, created = NeedSyncDevice.objects.get_or_create(
                card=card,
                device=device,
                defaults={
                    "need_sync": True,
                    "additional_info": {"failed_requests": [single_card_message]},
                },
            )
            if created:
                publish_updates("need_sync", "get_list_activity", {})

            if not created:
                info = sync_obj.additional_info or {"failed_requests": []}
                failed_requests = info.setdefault("failed_requests", [])

                if failed_requests and is_same_request(failed_requests[-1], single_card_message):
                    continue

                failed_requests.append(single_card_message)

                sync_obj.need_sync = True
                sync_obj.additional_info = info
                sync_obj.save()
                publish_updates("need_sync", "get_list_activity", {})



        except Card.DoesNotExist:
            logger.error("Card '%s' not found, skipping sync", card_num)
        except Exception as e:
            logger.error("Failed to update NeedSyncDevice for card '%s': '%s'", card_num, str(e))
