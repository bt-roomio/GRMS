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


def resolve_room_and_guest(tenant_id, room_name):
    if not room_name:
        raise LookupFailure("Missing required field: roomName")

    room = Room.objects.filter(tenant_id=tenant_id, number=room_name).first()
    if not room:
        raise LookupFailure(f"Room not found: {room_name}")

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

    room = Room.objects.filter(tenant_id=tenant_id, number=room_name).first()
    if not room:
        raise LookupFailure(f"Room not found: {room_name}")

    guests_qs = Guest.objects.filter(tenant_id=tenant_id, room=room, is_active=True)
    if reservation_number:
        guests_qs = guests_qs.filter(additional_info__pms_reg_num=reservation_number)

    guests = list(guests_qs.order_by("created_at"))
    if not guests:
        if reservation_number:
            raise LookupFailure(f"Guest not found for reservation {reservation_number} in room {room_name}")
        raise LookupFailure(f"No active guests in room {room_name}")
    return guests
