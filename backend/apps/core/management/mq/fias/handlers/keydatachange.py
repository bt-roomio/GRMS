import logging

from main.models import Guest, Room

from core.management.mq.fias.exceptions import LookupFailure
from core.management.mq.fias.utils.guests import resolve_entities
from core.management.mq.fias.utils.rpc import (
    send_card_operation_confirmation,
    send_rpc_to_guest_devices,
)

logger = logging.getLogger(__name__)


def handle_keydatachange(data, device):
    operation_id = data["operationId"]
    tenant_id = device.get("tenant_id")

    try:
        _, new_guest, card_uid = resolve_entities(
            tenant_id, data.get("roomName"), data.get("keyCoder")
        )
    except LookupFailure as e:
        logger.warning(
            "keydatachange lookup failed operationId=%s room=%s: %s",
            operation_id,
            data.get("roomName"),
            e,
        )
        send_card_operation_confirmation(device, operation_id, status="UR", text=str(e))
        return

    results = []
    old_room_name = data.get("oldRoomName")
    new_room_name = data.get("roomName")

    logger.info(
        "keydatachange operationId=%s card=%s oldRoom=%s newRoom=%s newGuest=%s",
        operation_id,
        card_uid,
        old_room_name,
        new_room_name,
        new_guest.id,
    )

    if old_room_name:
        results.append(_revoke_from_old_room(tenant_id, old_room_name, card_uid))

    newsuccess, new_text = send_rpc_to_guest_devices(new_guest, card_uid, access=1)
    results.append(f"New room {new_room_name}: {new_text}")

    status = "OK" if newsuccess else "UR"
    text = "Card room changed successfully" if newsuccess else "; ".join(results)
    if not newsuccess:
        logger.error(
            "keydatachange write failed operationId=%s card=%s results=%s",
            operation_id,
            card_uid,
            results,
        )
    send_card_operation_confirmation(device, operation_id, status=status, text=text)


def _revoke_from_old_room(tenant_id, old_room_name, card_uid):
    old_room = Room.objects.filter(
        tenant_id=tenant_id, number=old_room_name
    ).first()
    if not old_room:
        return f"Old room {old_room_name}: Room not found: {old_room_name}"

    old_guest = (
        Guest.objects.filter(room=old_room, is_active=True)
        .order_by("created_at")
        .first()
    )
    if not old_guest:
        return f"Old room {old_room_name}: Guest not found for room {old_room.number}"

    _, old_text = send_rpc_to_guest_devices(old_guest, card_uid, access=0)
    return f"Old room {old_room_name}: {old_text}"
