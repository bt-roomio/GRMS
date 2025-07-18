from access_manager.models import Group
from access_manager.utilits.need_sync import need_sync
from celery import shared_task
from celery.utils.log import get_task_logger

from access_manager.utilits.process_multi_devices_rpc import process_devices_parallel
from main.models import Device

logger = get_task_logger(__name__)


@shared_task(autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 60})
def manage_cards_for_public_space_task(group_id: str, public_space_id: str, action: str, card_num=None):
    """Connect or disconnect cards to/from public space devices."""
    try:
        access = 1 if action == "connect" else 0
        cards, group = Group.objects.get_staff_cards(group_id)
        cards = [card_num] if card_num else cards
        if not cards or not group:
            return {"success": False, "message": f"No cards found for group {group_id}"}

        active_devices, inactive_devices = Device.objects.active_inactive(public_space_id, group.tenant)

        for device in inactive_devices:
            logger.info(f"Adding device {device.name} (ID: {device.id}) to sync queue - inactive or status false")
            need_sync(cards, device, access)

        if not active_devices.exists():
            logger.info("No active devices found for public space '%s'", public_space_id)
            return {
                "success": False,
                "message": f"No active devices found for public space {public_space_id}",
            }

        devices_list = list(active_devices)
        results = process_devices_parallel(devices_list, cards, group, action)

        logger.info(
            "Completed manage_cards_for_public_space_task for group '%s' and public space '%s' with action '%s'",
            group_id,
            public_space_id,
            action,
        )

        return {
            "success": True,
            "message": f"{action.capitalize()}ed {len(cards)} cards to/from {len(devices_list)} active devices. {len(inactive_devices)} inactive devices added to sync queue.",
            "results": results,
            "processed_devices": len(devices_list),
            "synced_devices": len(inactive_devices),
        }

    except Group.DoesNotExist:
        logger.debug("Group '%s' not found or not active", group_id)
        return {"success": False, "message": f"Group {group_id} not found or not active"}
    except Exception as e:
        logger.error("Error in manage_cards_for_public_space_task: '%s'", str(e))
        raise e
