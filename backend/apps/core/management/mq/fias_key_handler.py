import json
import logging
import time

from access_manager.models import GuestCard, StaffCard, TypeChoices
from access_manager.tasks.send_rpc import send_rpc_request

from core.rabbitmq.config import connect_to_rabbitmq, send_to_rabbitmq
from main.models import Device, Guest, Room
from main.utils.access_context import get_guest_access_context
from shuttle.models import AttributeKv, Relation, RPCMessage

logger = logging.getLogger(__name__)

KEY_COMMANDS = {"keyrequest", "keydelete", "keydatachange", "keyread"}
CARD_ON_READER_TIMEOUT = 5
KEYREQUEST_COLLECTION_TIMEOUT = 45


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

    logger.debug("Sending confirmation message to %s", message)

    try:
        channel = connect_to_rabbitmq()
        send_to_rabbitmq(channel, message)
        channel.connection.close()

        logger.info("confirmCardOperation operationId=%s status=%s", operation_id, status)
    except Exception as exc:
        logger.exception("Failed confirmCardOperation operationId=%s: %s", operation_id, exc)
        raise


def _resolve_reader(tenant_id, key_coder):
    if not key_coder:
        raise _LookupFailure("Missing required field: keyCoder")

    logger.debug(f"Reading key from tenant {tenant_id}, key coder {key_coder}")
    reader = Device.objects.filter(name=key_coder, tenant_id=tenant_id, is_active=True).first()
    if not reader:
        raise _LookupFailure(f"Card reader is unavailable: {key_coder}")
    return reader


def _resolve_card_uid(tenant_id, key_coder):
    return _wait_for_card_on_reader(_resolve_reader(tenant_id, key_coder).id)


def _resolve_room_and_guest(tenant_id, room_name):
    if not room_name:
        raise _LookupFailure("Missing required field: roomName")

    room = Room.objects.filter(tenant_id=tenant_id, number=room_name).first()
    if not room:
        raise _LookupFailure(f"Room not found: {room_name}")

    guest = Guest.objects.filter(room=room, is_active=True).order_by("created_at").first()


    return room, guest


def _resolve_entities(tenant_id, room_name, key_coder):
    room, guest = _resolve_room_and_guest(tenant_id, room_name)
    card_uid = _resolve_card_uid(tenant_id, key_coder)
    return room, guest, card_uid


def _wait_for_card_on_reader(reader_device_id, timeout=CARD_ON_READER_TIMEOUT):
    start_time = time.time()
    while time.time() - start_time < timeout:
        card_on_reader = AttributeKv.objects.filter(
            entity_id=reader_device_id,
            attribute_type=AttributeKv.CLIENT_SCOPE,
            attribute_key="card_on_reader",
            bool_v=True,
        ).first()
        if card_on_reader:
            card_uid_attr = AttributeKv.objects.filter(
                entity_id=reader_device_id,
                attribute_type=AttributeKv.CLIENT_SCOPE,
                attribute_key="card_uid",
            ).first()
            card_uid = card_uid_attr.str_v if card_uid_attr else None
            if not card_uid:
                raise _LookupFailure("Card UID not found on reader")
            return card_uid
        time.sleep(0.5)
    raise _LookupFailure("Timeout waiting for card on reader")


def _collect_unique_cards(reader_device_id, count, timeout=KEYREQUEST_COLLECTION_TIMEOUT):
    collected = []
    seen = set()
    deadline = time.time() + timeout

    while len(collected) < count:
        if time.time() >= deadline:
            raise _LookupFailure(f"Timeout: collected {len(collected)} of {count} cards")

        on_reader = AttributeKv.objects.filter(
            entity_id=reader_device_id,
            attribute_type=AttributeKv.CLIENT_SCOPE,
            attribute_key="card_on_reader",
            bool_v=True,
        ).exists()
        if on_reader:
            card_uid_attr = AttributeKv.objects.filter(
                entity_id=reader_device_id,
                attribute_type=AttributeKv.CLIENT_SCOPE,
                attribute_key="card_uid",
            ).first()
            uid = card_uid_attr.str_v if card_uid_attr else None
            if uid and uid not in seen:
                seen.add(uid)
                collected.append(uid)
                if len(collected) >= count:
                    break
        time.sleep(0.5)
    return collected


def _find_conflicting_cards(tenant_id, card_uids, guest):
    conflicts = set(
        GuestCard.objects.filter(
            card__number__in=card_uids,
            card__tenant_id=tenant_id,
            is_active=True,
        )
        .exclude(guest=guest)
        .values_list("card__number", flat=True)
    )
    conflicts.update(
        StaffCard.objects.filter(
            card__number__in=card_uids,
            card__tenant_id=tenant_id,
            is_active=True,
        ).values_list("card__number", flat=True)
    )
    return sorted(conflicts)


def _parse_key_count(value):
    if value is None:
        return 1
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return 1


def send_rpc_to_guest_devices(guest, card_uid, access):
    context = get_guest_access_context(guest)
    devices = context.get("devices")
    if not devices:
        return False, "No devices found for guest room"

    if access == 0 and not context.get("guest_cards"):
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

    if access == 0 and not guest:
        send_card_operation_confirmation(device, operation_id, status="OK", text=success_text)
        return

    success, text = send_rpc_to_guest_devices(guest, card_uid, access=access)
    if success:
        text = success_text
    send_card_operation_confirmation(device, operation_id, status="OK" if success else "UR", text=text)


def handle_keyrequest(data, device):
    key_count = _parse_key_count(data.get("keyCount"))
    if key_count <= 1:
        handle_card_access(data, device, access=1, success_text="Guest card created successfully")
        return
    _handle_multi_card_keyrequest(data, device, key_count)


def _handle_multi_card_keyrequest(data, device, key_count):
    operation_id = data["operationId"]
    tenant_id = device.get("tenant_id")

    try:
        _, guest = _resolve_room_and_guest(tenant_id, data.get("roomName"))
        reader = _resolve_reader(tenant_id, data.get("keyCoder"))
        card_uids = _collect_unique_cards(reader.id, key_count)
    except _LookupFailure as e:
        send_card_operation_confirmation(device, operation_id, status="UR", text=str(e))
        return

    conflicts = _find_conflicting_cards(tenant_id, card_uids, guest)
    if conflicts:
        send_card_operation_confirmation(
            device,
            operation_id,
            status="UR",
            text=f"Cards already assigned: {', '.join(conflicts)}",
        )
        return

    errors = []
    for uid in card_uids:
        success, text = send_rpc_to_guest_devices(guest, uid, access=1)
        if not success:
            errors.append(f"{uid}: {text}")

    if errors:
        send_card_operation_confirmation(
            device,
            operation_id,
            status="UR",
            text=f"Failed to write cards: {'; '.join(errors)}",
        )
        return

    send_card_operation_confirmation(
        device,
        operation_id,
        status="OK",
        text=f"Created {len(card_uids)} guest cards successfully",
    )


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
        "holderType": "guest",
        "roomNumber": room.number if room else "",
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


def _build_staff_details(staff, card_uid):
    group = staff.group
    access_group_name = ""
    group_name = ""
    if group:
        group_name = group.name or ""
        if group.group_type is not None:
            try:
                access_group_name = TypeChoices(group.group_type).name
            except ValueError:
                access_group_name = ""
    return {
        "holderType": "staff",
        "cardUid": card_uid,
        "staffName": staff.get_name(),
        "staffFirstName": staff.first_name or "",
        "staffLastName": staff.last_name or "",
        "accessGroup": access_group_name,
        "groupName": group_name,
    }


def handle_keyread(data, device):
    operation_id = data["operationId"]
    tenant_id = device.get("tenant_id")

    try:
        card_uid = _resolve_card_uid(tenant_id, data.get("keyCoder"))
    except _LookupFailure as e:
        send_card_operation_confirmation(device, operation_id, status="UR", text=str(e))
        return

    guest_card = (
        GuestCard.objects.filter(
            card__number=card_uid,
            card__tenant_id=tenant_id,
            is_active=True,
        )
        .select_related("guest", "guest__room")
        .first()
    )

    if guest_card and guest_card.guest:
        details = _build_guest_details(guest_card.guest, guest_card.guest.room)
        send_card_operation_confirmation(device, operation_id, status="OK", text=json.dumps(details))
        return

    staff_card = (
        StaffCard.objects.filter(
            card__number=card_uid,
            card__tenant_id=tenant_id,
            is_active=True,
        )
        .select_related("staff", "staff__group")
        .first()
    )

    if staff_card and staff_card.staff:
        details = _build_staff_details(staff_card.staff, card_uid)
        send_card_operation_confirmation(device, operation_id, status="OK", text=json.dumps(details))
        return

    send_card_operation_confirmation(
        device, operation_id, status="UR", text=f"Card does not belong to any guest or staff: {card_uid}"
    )


KEY_COMMAND_HANDLERS = {
    "keyrequest": handle_keyrequest,
    "keydelete": handle_keydelete,
    "keydatachange": handle_keydatachange,
    "keyread": handle_keyread,
}
