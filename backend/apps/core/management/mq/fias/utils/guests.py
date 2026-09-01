import logging
from datetime import time as time_cls

from core.management.mq.fias.constants import CARD_ON_READER_TIMEOUT
from core.management.mq.fias.exceptions import LookupFailure
from core.management.mq.fias.utils.readers import collect_unique_cards
from main.models import Device, Guest, Room, Tenant

logger = logging.getLogger(__name__)

SECONDS_IN_DAY = 86400


def override_checkout_time(tenant_id, departure_ts):
    try:
        ts = int(departure_ts)
    except (TypeError, ValueError):
        return departure_ts

    if ts > 1e12:
        ts //= 1000

    tenant = Tenant.objects.filter(id=tenant_id).first()
    if not tenant:
        return departure_ts

    g_settings = (tenant.additional_info or {}).get("general_settings", {})
    checkout_time = time_cls.fromisoformat(str(g_settings.get("auto_checkout_time") or "12:00:00"))
    day_start = ts - (ts % SECONDS_IN_DAY)
    checkout_datetime = day_start + checkout_time.hour * 3600 + checkout_time.minute * 60 + checkout_time.second

    return checkout_datetime


def resolve_reader(tenant_id, key_coder):
    if not key_coder:
        raise LookupFailure("Missing required field: keyCoder")

    logger.debug("Reading key from tenant %s, key coder %s", tenant_id, key_coder)
    reader = Device.objects.filter(name=key_coder, tenant_id=tenant_id, is_active=True).first()
    if not reader:
        raise LookupFailure(f"Card reader is unavailable: {key_coder}")
    return reader


def resolve_card_uid(tenant_id, key_coder):
    reader = resolve_reader(tenant_id, key_coder)
    return collect_unique_cards(reader.id, count=1, timeout=CARD_ON_READER_TIMEOUT)[0]


def resolve_room(tenant_id, room_name):
    room = Room.objects.filter(tenant_id=tenant_id, number=room_name).first()
    if not room:
        raise LookupFailure(f"Room not found: {room_name}")
    return room


def resolve_room_and_guest(tenant_id, room_name):
    if not room_name:
        raise LookupFailure("Missing required field: roomName")

    room = resolve_room(tenant_id, room_name)

    guest = Guest.objects.filter(room=room, is_active=True).order_by("created_at").first()
    if not guest:
        raise LookupFailure(f"No active guest in room {room_name}")

    return room, guest


def resolve_entities(tenant_id, room_name, key_coder):
    room, guest = resolve_room_and_guest(tenant_id, room_name)
    card_uid = resolve_card_uid(tenant_id, key_coder)
    return room, guest, card_uid


def resolve_guests_for_keydelete(tenant_id, room_name, reservation_number):
    if not room_name:
        raise LookupFailure("Missing required field: roomName")

    room = resolve_room(tenant_id, room_name)

    guests_qs = Guest.objects.filter(tenant_id=tenant_id, room=room, is_active=True)
    if reservation_number:
        guests_qs = guests_qs.filter(additional_info__pms_reg_num=reservation_number)

    guests = list(guests_qs.order_by("created_at"))
    if not guests:
        if reservation_number:
            raise LookupFailure(f"Guest not found for reservation {reservation_number} in room {room_name}")
        raise LookupFailure(f"No active guests in room {room_name}")
    return guests


def resolve_guests_for_datachange(tenant_id, reservation_number, old_room_name, room_name):
    """Find every active guest a FIAS `datachange` applies to.

    `pms_reg_num` is not unique — `CheckInSerializer` matches on it without room scoping,
    so a recycled reservation number can hit a stale stay. Whenever `oldRoomName` is
    given it wins: guests are taken from that room, narrowed by reservation number only
    when that narrowing actually matches something.
    """
    guests = Guest.objects.filter(tenant_id=tenant_id, is_active=True)

    if old_room_name:
        matched = _guests_in_room(guests, tenant_id, old_room_name, reservation_number)
    elif reservation_number:
        # No oldRoomName means no move, so the target room says nothing about who this is:
        # guessing by it would stamp the message onto whoever happens to live there.
        matched = guests.filter(additional_info__pms_reg_num=reservation_number)
        if not matched.exists():
            raise LookupFailure(f"Reservation {reservation_number} not found")
    else:
        matched = _guests_in_room(guests, tenant_id, room_name, None)

    # A guest with no room cannot be moved: handle_guest_move() dereferences the old room
    resolved = [guest for guest in matched.order_by("created_at") if guest.room_id]

    skipped = matched.count() - len(resolved)
    if skipped:
        logger.warning("datachange skipped %s guest(s) without a room in %s", skipped, old_room_name or room_name)
    if not resolved:
        raise LookupFailure(
            f"No active guest found for reservation {reservation_number} / room {old_room_name or room_name}"
        )

    return resolved


def _guests_in_room(guests, tenant_id, room_name, reservation_number):
    """Guests of `reservation_number` in `room_name`, or the whole room when it holds one stay.

    Guests booked outside FIAS carry no `pms_reg_num`, so an empty narrowing falls back to
    the room — but only while no other reservation claims it, otherwise a co-tenant on a
    different booking would be dragged along.
    """
    in_room = guests.filter(room=resolve_room(tenant_id, room_name))
    if not reservation_number:
        return in_room

    matched = in_room.filter(additional_info__pms_reg_num=reservation_number)
    if matched.exists():
        return matched

    # Checked in Python rather than via `additional_info__pms_reg_num__isnull`: that lookup
    # compiles to `-> 'pms_reg_num' IS NOT NULL`, which a stored JSON null also satisfies.
    if any((info or {}).get("pms_reg_num") for info in in_room.values_list("additional_info", flat=True)):
        raise LookupFailure(f"Reservation {reservation_number} not found in room {room_name}")

    return in_room
