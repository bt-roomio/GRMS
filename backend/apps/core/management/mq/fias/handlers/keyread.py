import json
import logging

from access_manager.utilits.check_card_assignment import get_card_holder
from core.management.mq.fias.exceptions import LookupFailure
from core.management.mq.fias.utils.guests import resolve_card_uid
from core.management.mq.fias.utils.payloads import build_card_holder_details
from core.management.mq.fias.utils.rpc import send_card_operation_confirmation

logger = logging.getLogger(__name__)


def handle_keyread(data, device):
    operation_id = data["operationId"]
    tenant_id = device.get("tenant_id")

    try:
        card_uid = resolve_card_uid(tenant_id, data.get("keyCoder"))
    except LookupFailure as e:
        logger.warning("keyread lookup failed operationId=%s: %s", operation_id, e)
        send_card_operation_confirmation(device, operation_id, status="UR", text=str(e))
        return

    holder_type, holder = get_card_holder(tenant_id, card_uid)
    details = build_card_holder_details(holder_type, holder, card_uid)
    if details:
        logger.info(
            "keyread operationId=%s card=%s holderType=%s",
            operation_id,
            card_uid,
            holder_type,
        )
        send_card_operation_confirmation(device, operation_id, status="OK", text=json.dumps(details))
        return

    logger.warning("keyread unassigned card operationId=%s card=%s", operation_id, card_uid)
    send_card_operation_confirmation(
        device,
        operation_id,
        status="UR",
        text=f"Card does not belong to any guest or staff: {card_uid}",
    )
