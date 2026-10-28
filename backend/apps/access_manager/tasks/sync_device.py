import logging
from collections import defaultdict

from celery import shared_task
from django.db.models import Exists, OuterRef

from access_manager.models import NeedSyncDevice
from access_manager.tasks.send_rpc import send_rpc_request
from main.models import Device, DevicePublicSpaces, Guest, Room

logger = logging.getLogger("main")


@shared_task(autoretry_for=(Exception,), retry_kwargs={"max_retries": 3, "countdown": 60})
def sync_device_card_group(device_id, cards, access, is_pwd=False, source=None, user_id=None):
    # `source`/`user_id` are recorded on the guest cards; requests queued before the source was stored count as AUTO.
    source = source or Guest.SOURCE.AUTO
    # Default-profile devices take the full card list in one writeRFID; everything else
    # (PINs and non-default devices) is synced one card per request.
    is_default = Device.objects.filter(id=device_id, device_profile__name__iexact="default").exists()
    batches = [cards] if is_default and not is_pwd else [[card] for card in cards]

    for batch in batches:
        result = send_rpc_request(device_id, batch, access, user=user_id, sync=True, is_pwd=is_pwd, source=source)
        if result.get("success", False):
            NeedSyncDevice.objects.filter(
                device_id=device_id,
                card__number__in=batch,
                need_sync=True,
            ).update(need_sync=False)


@shared_task(autoretry_for=(Exception,), retry_kwargs={"max_retries": 3, "countdown": 60})
def sync_devices_task(tenant_id=None, ids=None, device_ids=None, user_id=None):
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
            message_params = (obj.additional_info or {}).get("message_params", {})
            access = message_params.get("access", "UNKNOWN")
            if user_id:
                source, actor_id = Guest.SOURCE.ROOMIO, user_id
            else:
                source, actor_id = message_params.get("source"), obj.updated_by_id and str(obj.updated_by_id)
            is_pwd = bool(obj.card.is_pwd)
            grouped[(device_id, access, is_pwd, source, actor_id)].append(obj.card.number)

        for (device_id, access, is_pwd, source, actor_id), cards in grouped.items():
            sync_device_card_group.delay(str(device_id), cards, access, is_pwd, source=source, user_id=actor_id)

        return {"success": True, "dispatched": len(grouped)}

    except Exception as e:
        logger.error("sync_devices_task error: %s", str(e))
        raise e
