from celery import shared_task
from celery.utils.log import get_task_logger

from access_manager.models import Group
from access_manager.utilits.process_multi_devices_rpc import process_devices_parallel
from main.models import Device

logger = get_task_logger(__name__)


@shared_task(autoretry_for=(Exception,), retry_kwargs={"max_retries": 3, "countdown": 60})
def manage_cards_for_room_task(group_id: str, room_id: str, action: str, card_num=None):
    try:
        logger.info("Managing cards for room=%s: action=%s group=%s", room_id, action, group_id)
        cards, group = Group.objects.get_staff_cards(group_id)
        cards = [card_num] if card_num else cards
        if not cards or not group:
            return {"success": False, "message": f"No cards found for group {group_id}"}

        door_lock_devices = Device.objects.filter(
            as_door_lock_room=room_id, tenant=group.tenant, is_active=True
        ).distinct()

        if door_lock_devices.exists():
            devices = door_lock_devices
        else:
            devices = Device.objects.filter(room_id=room_id, tenant=group.tenant, is_active=True)

        if not devices.exists():
            logger.info("No active devices for room=%s in tenant=%s", room_id, group.tenant)
            return {"success": False, "message": f"No active devices found for room {room_id} in tenant {group.tenant}"}

        results = process_devices_parallel(devices, cards, group, action)

        return {
            "success": True,
            "message": f"{action.capitalize()}ed {len(cards)} cards to/from {devices.count()} devices",
            "results": results,
        }

    except Group.DoesNotExist:
        return {"success": False, "message": f"Group {group_id} not found or not active"}
    except Exception as e:
        raise e
