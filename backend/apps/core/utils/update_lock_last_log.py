import logging
from typing import Optional

from django.db import transaction

from main.models import Device
from shuttle.models import AttributeKv

logger = logging.getLogger(__name__)


def update_lock_last_log_id(tenant_id: str, access_log_id, lock_type: str, device_id: Optional[str] = None) -> None:
    lock_type = (lock_type or "").strip().lower()
    try:
        new_ts = int(access_log_id)
    except (TypeError, ValueError):
        return

    try:
        if lock_type == "ttlock":
            device = Device.objects.get(id=device_id)
        else:
            device = (
                Device.objects.filter(tenant_id=tenant_id, name__startswith="HRC350_LOCK", is_active=True)
                .order_by("id")
                .first()
            )

        if not device:
            return

        update_device_shared_int_if_bigger(
            device=device,
            attribute_key=f"{lock_type}LastLogId",
            new_value=new_ts,
        )

    except Exception as e:
        logger.error("Error triggering last-log update for tenant %s: %s", tenant_id, e)


def update_device_shared_int_if_bigger(device: Device, attribute_key: str, new_value: int):
    try:
        with transaction.atomic():
            attr, created = AttributeKv.objects.select_for_update().get_or_create(
                entity=device,
                entity_type="DEVICE",
                attribute_type=AttributeKv.SHARED_SCOPE,
                attribute_key=attribute_key,
                defaults={"str_v": str(new_value)},
            )

            if created:
                return

            old_id = int(attr.str_v)
            if old_id is None or new_value > old_id:
                attr.str_v = str(new_value)
                attr.save(update_fields=["str_v"])

    except Exception as e:
        logger.error(
            "Error updating shared attr %s for device %s: %s", attribute_key, getattr(device, "name", "unknown"), e
        )
