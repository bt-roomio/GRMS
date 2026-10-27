from functools import partial
from typing import List

from celery.utils.log import get_task_logger
from django.db import transaction

from access_manager.utilits.check_card_assignment import get_card_assignments
from shuttle.services.publish_updates import publish_updates

logger = get_task_logger(__name__)


def need_sync(cards: List[str], device, access, user=None, reason="", source=None):
    """Queue the request for sync_devices_task; `user` and `source` are replayed with it."""
    from access_manager.models import Card, NeedSyncDevice

    if not device:
        return

    assignments = get_card_assignments(cards, device.tenant_id)
    cards_with_assignment = [c for c in cards if c in assignments]
    target_cards = cards_with_assignment if access else cards

    if not target_cards:
        return

    changed = False
    for card_num in target_cards:
        try:
            card = Card.objects.get(number=card_num, tenant=device.tenant)

            message_params = {"access": access, "reason": reason, "source": source}

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
            if not created:
                info = sync_obj.additional_info or {}
                info["message_params"] = message_params

                sync_obj.need_sync = True
                sync_obj.updated_by_id = user
                sync_obj.additional_info = info
                sync_obj.save()
            changed = True

        except Card.DoesNotExist:
            logger.error("Card '%s' not found, skipping sync", card_num)
        except Exception as e:
            logger.error("Failed to update NeedSyncDevice for card '%s': '%s'", card_num, str(e))

    # One notification per call rather than per card: the subscriber re-reads the
    # whole list on every message. Sent after commit, otherwise it would re-read
    # stale data.
    if changed:
        transaction.on_commit(partial(publish_updates, f"need_sync_{device.tenant_id}", "get_list_activity", {}))
