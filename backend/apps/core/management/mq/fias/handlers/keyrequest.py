import logging

from access_manager.utilits.check_card_assignment import get_card_assignments

from core.management.mq.fias.constants import KEYREQUEST_COLLECTION_TIMEOUT
from core.management.mq.fias.exceptions import LookupFailure
from core.management.mq.fias.utils.cards import parse_key_count
from core.management.mq.fias.utils.guests import resolve_reader, resolve_room_and_guest
from core.management.mq.fias.utils.readers import collect_unique_cards
from core.management.mq.fias.utils.rpc import (
    send_card_operation_confirmation,
    send_rpc_to_guest_devices,
)

logger = logging.getLogger(__name__)


def handle_keyrequest(data, device):
    key_count = parse_key_count(data.get("keyCount"))
    operation_id = data["operationId"]
    tenant_id = device.get("tenant_id")
    room_name = data.get("roomName")

    try:
        _, guest = resolve_room_and_guest(tenant_id, room_name)
        reader = resolve_reader(tenant_id, data.get("keyCoder"))
        card_uids = collect_unique_cards(
            reader.id, key_count, timeout=KEYREQUEST_COLLECTION_TIMEOUT
        )
    except LookupFailure as e:
        logger.warning(
            "keyrequest lookup failed operationId=%s room=%s: %s",
            operation_id,
            room_name,
            e,
        )
        send_card_operation_confirmation(device, operation_id, status="UR", text=str(e))
        return

    conflicts = get_card_assignments(card_uids, tenant_id, exclude_guest_id=guest.id)
    if conflicts:
        logger.warning(
            "keyrequest conflict operationId=%s guest=%s cards=%s",
            operation_id,
            guest.id,
            sorted(conflicts),
        )
        send_card_operation_confirmation(
            device,
            operation_id,
            status="UR",
            text=f"Cards already assigned: {', '.join(sorted(conflicts))}",
        )
        return

    write_guest_cards(guest, card_uids, operation_id, device)


def write_guest_cards(guest, card_uids, operation_id, device):
    errors = []
    for uid in card_uids:
        success, text = send_rpc_to_guest_devices(guest, uid, access=1)
        if not success:
            errors.append(f"{uid}: {text}")

    if errors:
        logger.error(
            "keyrequest write failed operationId=%s guest=%s errors=%s",
            operation_id,
            guest.id,
            errors,
        )
        send_card_operation_confirmation(
            device,
            operation_id,
            status="UR",
            text=f"Failed to write cards: {'; '.join(errors)}",
        )
        return

    success_text = (
        "Guest card created successfully"
        if len(card_uids) == 1
        else f"Created {len(card_uids)} guest cards successfully"
    )
    send_card_operation_confirmation(
        device, operation_id, status="OK", text=success_text
    )
