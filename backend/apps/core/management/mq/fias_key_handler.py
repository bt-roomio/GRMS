import json
import logging
import time

from access_manager.models import GuestCard
from access_manager.tasks.send_rpc import send_rpc_request

from core.rabbitmq.config import connect_to_rabbitmq, send_to_rabbitmq
from main.models import Device, Guest, Room
from main.utils.access_context import get_guest_access_context
from shuttle.models import AttributeKv, Relation, RPCMessage

logger = logging.getLogger(__name__)

KEY_COMMANDS = {"keyrequest", "keydelete", "keydatachange", "keyread"}
CARD_ON_READER_TIMEOUT = 5


class _LookupFailure(Exception):
    pass


def send_card_operation_confirmation(device, operation_id, status="OK", text=""):
    relation = Relation.objects.filter(to_id_id=device["id"]).order_by("updated_at").last()
    device_id = relation and relation.from_id.id
    gateway_or_none = Device.objects.gateway_or_none(device["id"])  # pyright: ignore

    rpc_message = RPCMessage.objects.create(additional_info={})
    request_id = rpc_message.id

    message = {
        "targetDeviceUUID": (gateway_or_none and str(gateway_or_none.id)) or str(device_id),
        "topic": "v1/gateway/rpc",
        "data": {
            "device": str(device["name"]),
            "data": {
                "id": request_id,
                "method": "confirmCardOperation",
                "params": {
                    "operationId": operation_id,
                    "status": status,
                    "text": text,
                },
            },
        },
    }

    try:
        channel = connect_to_rabbitmq()
        send_to_rabbitmq(channel, message)
        channel.connection.close()

        logger.info("confirmCardOperation operationId=%s status=%s", operation_id, status)
    except Exception as exc:
        logger.exception("Failed confirmCardOperation operationId=%s: %s", operation_id, exc)
        raise


def _resolve_entities(tenant_id, room_name, key_coder):
    if not room_name:
        raise _LookupFailure("Missing required field: roomName")
    if not key_coder:
        raise _LookupFailure("Missing required field: keyCoder")

    room = Room.objects.filter(tenant_id=tenant_id, number=room_name).first()
    if not room:
        raise _LookupFailure(f"Room not found: {room_name}")

    guest = Guest.objects.filter(room=room, is_active=True).order_by("created_at").first()
    if not guest:
        raise _LookupFailure(f"Guest not found for room {room.number}")

    reader = Device.objects.filter(name=key_coder, tenant_id=tenant_id, is_active=True).first()
    if not reader:
        raise _LookupFailure(f"Card reader is unavailable: {key_coder}")

    card_uid = _wait_for_card_on_reader(reader.id)

    return room, guest, card_uid


def _wait_for_card_on_reader(reader_device_id, timeout=CARD_ON_READER_TIMEOUT):
    start_time = time.time()
    while time.time() - start_time < timeout:
        card_on_reader = AttributeKv.objects.filter(
            entity_id=reader_device_id,
            attribute_type=AttributeKv.CLIENTsCOPE,
            attribute_key="card_on_reader",
            bool_v=True,
        ).first()
        if card_on_reader:
            card_uid_attr = AttributeKv.objects.filter(
                entity_id=reader_device_id,
                attribute_type=AttributeKv.CLIENTsCOPE,
                attribute_key="card_uid",
            ).first()
            card_uid = card_uid_attr.str_v if card_uid_attr else None
            if not card_uid:
                raise _LookupFailure("Card UID not found on reader")
            return card_uid
        time.sleep(0.5)
    raise _LookupFailure("Timeout waiting for card on reader")


def send_rpc_to_guest_devices(guest, card_uid, access):
    context = get_guest_access_context(guest)
    devices = context.get("devices")
    if not devices:
        return False, "No devices found for guest room"

    guest_card = GuestCard.objects.filter(card__number=card_uid, guest=guest, is_active=True).exists()
    if access == 0 and not guest_card:
        return True, "Operation completed"

    errors = []
    successes = []
    for dev in devices:
        result = send_rpc_request(str(dev.id), [card_uid], access, guest_id=str(guest.id))
        if result.get("success"):
            successes.append(result.get("message", "OK"))
        else:
            errors.append(result.get("message", "Failed"))

    if errors:
        return False, "; ".join(errors)
    return True, "; ".join(successes) if successes else "Operation completed"


def handle_card_access(data, device, access, success_text):
    operation_id = data["operationId"]
    try:
        room, guest, card_uid = _resolve_entities(device.get("tenant_id"), data.get("roomName"), data.get("keyCoder"))
    except _LookupFailure as e:
        send_card_operation_confirmation(device, operation_id, status="UR", text=str(e))
        return

    success, text = send_rpc_to_guest_devices(guest, card_uid, access=access)
    if success:
        text = success_text
    send_card_operation_confirmation(device, operation_id, status="OK" if success else "UR", text=text)


def handle_keyrequest(data, device):
    handle_card_access(data, device, access=1, success_text="Guest card created successfully")


def handle_keydelete(data, device):
    handle_card_access(data, device, access=0, success_text="Guest card deleted successfully")


def handle_keydatachange(data, device):
    operation_id = data["operationId"]
    tenant_id = device.get("tenant_id")

    try:
        new_room, new_guest, card_uid = _resolve_entities(tenant_id, data.get("roomName"), data.get("keyCoder"))
    except _LookupFailure as e:
        send_card_operation_confirmation(device, operation_id, status="UR", text=str(e))
        return

    results = []
    old_room_name = data.get("oldRoomName")

    if old_room_name:
        old_room = Room.objects.filter(tenant_id=tenant_id, number=old_room_name).first()
        if old_room:
            old_guest = Guest.objects.filter(room=old_room, is_active=True).order_by("created_at").first()
            if old_guest:
                oldsuccess, old_text = send_rpc_to_guest_devices(old_guest, card_uid, access=0)
                results.append(f"Old room {old_room_name}: {old_text}")
            else:
                results.append(f"Old room {old_room_name}: Guest not found for room {old_room.number}")
        else:
            results.append(f"Old room {old_room_name}: Room not found: {old_room_name}")

    new_room_name = data.get("roomName")
    newsuccess, new_text = send_rpc_to_guest_devices(new_guest, card_uid, access=1)
    results.append(f"New room {new_room_name}: {new_text}")

    status = "OK" if newsuccess else "UR"
    text = "Card room changed successfully" if newsuccess else "; ".join(results)
    send_card_operation_confirmation(device, operation_id, status=status, text=text)


def _build_guest_details(guest, room):
    additional_info = guest.additional_info or {}
    return {
        "roomNumber": room.number,
        "guestName": guest.name,
        "guestFirstName": guest.lastname or "",
        "guestTitle": guest.title or "",
        "pmsRegNum": additional_info.get("pms_reg_num", ""),
        "arrivalDateTS": guest.check_in,
        "departureDateTS": guest.check_out,
        "guestLanguage": guest.language or "",
        "roomShare": additional_info.get("roomshare", ""),
        "nopost": additional_info.get("no_post", ""),
        "profileNum": additional_info.get("profile_num", ""),
    }


def handle_keyread(data, device):
    operation_id = data["operationId"]
    tenant_id = device.get("tenant_id")

    try:
        room, guest, card_uid = _resolve_entities(tenant_id, data.get("roomName"), data.get("keyCoder"))
    except _LookupFailure as e:
        send_card_operation_confirmation(device, operation_id, status="UR", text=str(e))
        return

    guest_card = (
        GuestCard.objects.filter(
            card__number=card_uid,
            card__tenant_id=tenant_id,
            guest__room=room,
            is_active=True,
        )
        .select_related("guest")
        .first()
    )

    if guest_card:
        details = _build_guest_details(guest_card.guest, room)
        send_card_operation_confirmation(device, operation_id, status="OK", text=json.dumps(details))
    else:
        send_card_operation_confirmation(
            device, operation_id, status="UR", text=f"Card does not belong to any guest of room {room.number}"
        )


KEY_COMMAND_HANDLERS = {
    "keyrequest": handle_keyrequest,
    "keydelete": handle_keydelete,
    "keydatachange": handle_keydatachange,
    "keyread": handle_keyread,
}
