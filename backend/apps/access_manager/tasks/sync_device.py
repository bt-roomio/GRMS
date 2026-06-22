import logging
from collections import defaultdict

from celery import shared_task
from django.db.models import Exists, OuterRef

from access_manager.models import NeedSyncDevice
from access_manager.tasks.send_rpc import send_rpc_request
from main.models import DevicePublicSpaces, Room

logger = logging.getLogger("main")


@shared_task(autoretry_for=(Exception,), retry_kwargs={"max_retries": 3, "countdown": 60})
def sync_device_card_group(device_id, cards, access, is_pwd=False):
    if is_pwd:
        for card_number in cards:
            result = send_rpc_request(device_id, [card_number], access, sync=True, is_pwd=True)
            if result.get("success", False):
                NeedSyncDevice.objects.filter(
                    device_id=device_id, card__number=card_number, need_sync=True
                ).update(need_sync=False)
    else:
        result = send_rpc_request(device_id, cards, access, sync=True)
        if result.get("success", False):
            NeedSyncDevice.objects.filter(device_id=device_id, need_sync=True).update(need_sync=False)


@shared_task(autoretry_for=(Exception,), retry_kwargs={"max_retries": 3, "countdown": 60})
def sync_devices_task(tenant_id=None, ids=None, device_ids=None):
    try:
        queryset = (
            NeedSyncDevice.objects.select_related("device", "card")
            .prefetch_related("card__staffcard_set__staff__group", "card__guestcard_set__guest")
            .filter(
                need_sync=True,
                device__is_active=True,
            )
            .annotate(
                has_public_space=Exists(DevicePublicSpaces.objects.filter(device_id=OuterRef("device_id"))),
                has_door_lock=Exists(Room.objects.filter(door_lock_device_id=OuterRef("device_id"))),
            )
        )

        if tenant_id:
            queryset = queryset.filter(device__tenant_id=tenant_id)
        if ids:
            queryset = queryset.filter(id__in=ids)
        elif device_ids:
            queryset = queryset.filter(device_id__in=device_ids)

        need_sync_objects = list(queryset)

        if not need_sync_objects:
            return {"success": True, "message": "No cards to sync", "processed": 0}

        disconnected_ids = [
            obj.id
            for obj in need_sync_objects
            if obj.device.room_id is None and not obj.has_public_space and not obj.has_door_lock
        ]
        if disconnected_ids:
            NeedSyncDevice.objects.filter(id__in=disconnected_ids).update(need_sync=False)

        connected_objects = [obj for obj in need_sync_objects if obj.id not in set(disconnected_ids)]

        if not connected_objects:
            return {"success": True, "message": "No cards to sync", "processed": 0}

        grouped = defaultdict(list)
        for obj in connected_objects:
            device_id = obj.device_id
            access = (obj.additional_info or {}).get("message_params", {}).get("access", "UNKNOWN")
            is_pwd = bool(obj.card.is_pwd)
            grouped[(device_id, access, is_pwd)].append(obj.card.number)

        for (device_id, access, is_pwd), cards in grouped.items():
            sync_device_card_group.delay(str(device_id), cards, access, is_pwd)

        return {"success": True, "dispatched": len(grouped)}

    except Exception as e:
        logger.error("sync_devices_task error: %s", str(e))
        raise e
