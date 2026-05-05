import logging
from collections import defaultdict

from access_manager.models import NeedSyncDevice
from access_manager.tasks.send_rpc import send_rpc_request
from celery import shared_task
from django.db.models import Exists, OuterRef

from main.models import DevicePublicSpaces, Room

logger = logging.getLogger("main")


@shared_task(autoretry_for=(Exception,), retry_kwargs={"max_retries": 3, "countdown": 60})
def sync_devices_task(tenant_id=None, ids=None, device_ids=None):
    try:
        queryset = NeedSyncDevice.objects.select_related(
            "device", "card"
        ).prefetch_related(
            "card__staffcard_set__staff__group",
            "card__guestcard_set__guest"
        ).filter(
            need_sync=True,
            device__is_active=True,
        ).annotate(
            has_public_space=Exists(DevicePublicSpaces.objects.filter(device_id=OuterRef("device_id"))),
            has_door_lock=Exists(Room.objects.filter(door_lock_device_id=OuterRef("device_id"))),
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
            obj.id for obj in need_sync_objects
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
            grouped[(device_id, access)].append(obj.card.number)

        for (device_id, access), cards in grouped.items():
            result = send_rpc_request(str(device_id), cards, access, sync=True)
            if result.get("success", False):
                queryset.filter(device_id=device_id).update(need_sync=False)

        return {"success": True, "processed": len(connected_objects)}

    except Exception as e:
        logger.error("sync_devices_task error: %s", str(e))
        raise e
