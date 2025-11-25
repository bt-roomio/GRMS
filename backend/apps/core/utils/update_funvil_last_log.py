import logging

from django.db import transaction

from main.models import Device
from shuttle.models import AttributeKv

logger = logging.getLogger(__name__)


def update_fanvil_last_log_id(tenant_id, fanvil_access_log_id):
    try:
        device = Device.objects.filter(
            tenant_id=tenant_id,
            name__startswith="HRC350_FANVIL",
            is_active=True,
        ).order_by("id").first()

        if not device:
            logger.warning("No HRC350_FANVIL device found for tenant %s when updating fanvilLastLogId", tenant_id)
            return

        with transaction.atomic():
            AttributeKv.objects.update_or_create(
                entity=device, entity_type="DEVICE",
                attribute_type=AttributeKv.SERVER_SCOPE,
                attribute_key="fanvilLastLogId",
                defaults={"str_v": str(fanvil_access_log_id), "bool_v": None,
                          "long_v": None, "dbl_v": None, "json_v": None}
            )

    except Exception as e:
        logger.error("Error updating fanvilLastLogId for tenant %s: %s", tenant_id, e)
