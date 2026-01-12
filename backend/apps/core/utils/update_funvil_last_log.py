import logging

from django.db import transaction

from main.models import Device
from shuttle.models import AttributeKv

logger = logging.getLogger(__name__)


def update_lock_last_log_id(tenant_id, access_log_id, lock_type):
    try:
        log_id = int(access_log_id)
    except (TypeError, ValueError):
        return

    try:
        device = (
            Device.objects
            .filter(tenant_id=tenant_id, name__startswith="HRC350_LOCK", is_active=True)
            .order_by("id")
            .first()
        )
        if not device:
            return

        with transaction.atomic():
            attr, created = (
                AttributeKv.objects.select_for_update()
                .get_or_create(
                    entity=device,
                    entity_type="DEVICE",
                    attribute_type=AttributeKv.SHARED_SCOPE,
                    attribute_key=f"{lock_type}LastLogId",
                    defaults={"str_v": str(log_id)},
                )
            )

            if created:
                return

            old_id = int(attr.str_v)
            if old_id is None or log_id > old_id:
                attr.str_v = str(log_id)
                attr.save(update_fields=["str_v"])

    except Exception as e:
        logger.error("Error updating %s LastLogId for tenant %s: %s", lock_type, tenant_id, e)
