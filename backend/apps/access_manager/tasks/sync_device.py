import logging
from collections import defaultdict
from celery import shared_task

from access_manager.models import NeedSyncDevice
from access_manager.tasks.send_rpc import send_rpc_request

logger = logging.getLogger("main")


@shared_task(autoretry_for=(Exception,), retry_kwargs={"max_retries": 3, "countdown": 60})
def sync_devices_task(tenant_id, ids=None, device_ids=None):
    try:
        queryset = NeedSyncDevice.objects.select_related(
            "device", "card"
        ).prefetch_related(
            "card__staffcard_set__staff__group",
            "card__guestcard_set__guest"
        ).filter(
            need_sync=True,
            device__is_active=True,
            device__tenant_id=tenant_id
        )

        if ids:
            queryset = queryset.filter(id__in=ids)
        elif device_ids:
            queryset = queryset.filter(device_id__in=device_ids)

        need_sync_objects = list(queryset)

        if not need_sync_objects:
            return {"success": True, "message": "No cards to sync", "processed": 0}

        grouped = defaultdict(list)
        for obj in need_sync_objects:
            device_id = obj.device_id
            access = (obj.additional_info or {}).get("message_params", {}).get("access", "UNKNOWN")
            grouped[(device_id, access)].append(obj.card.number)

        for (device_id, access), cards in grouped.items():
            result = send_rpc_request(str(device_id), cards, access, sync=True)
            if result.get("success", False):
                queryset.filter(device_id=device_id).update(need_sync=False)

        return {"success": True, "processed": len(need_sync_objects)}

    except Exception as e:
        logger.error("sync_devices_task error: %s", str(e))
        raise e
