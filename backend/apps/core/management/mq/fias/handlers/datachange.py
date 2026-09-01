import logging

from django.db import transaction

from core.management.mq.fias.exceptions import LookupFailure
from core.management.mq.fias.utils.guests import resolve_guests_for_datachange, resolve_room
from core.management.mq.fias.utils.payloads import build_guest_move_payload
from core.utils.date import datetime_to_unix
from services.management.commands.pms_handler import handle_guest_move

logger = logging.getLogger(__name__)


def handle_datachange(data, device):
    """Apply a FIAS `datachange` event: move the reservation to `roomName` and refresh guest data.

    `oldRoomName` carries the room being left and identifies the guests unambiguously;
    when it is absent (a plain data update) they are looked up by reservation number.
    A reservation can hold several guests (`shareFlag`), so all of them are moved.
    """
    tenant_id = str(device.get("tenant_id"))
    room_name = data.get("roomName")
    old_room_name = data.get("oldRoomName")
    reservation_number = data.get("reservationNumber")

    if not room_name:
        raise LookupFailure("Missing required field: roomName")

    new_room = resolve_room(tenant_id, room_name)
    guests = resolve_guests_for_datachange(tenant_id, reservation_number, old_room_name, room_name)

    logger.info(
        "datachange reservation=%s oldRoom=%s newRoom=%s guests=%s",
        reservation_number,
        old_room_name,
        room_name,
        [str(guest.id) for guest in guests],
    )

    # A FIAS message carries one guest's identity, so name/language may only be applied
    # when it unambiguously belongs to that guest; a group gets the room and dates only.
    with_identity = len(guests) == 1
    if not with_identity:
        logger.warning(
            "datachange matched %s guests on reservation %s; applying room and dates only",
            len(guests),
            reservation_number,
        )

    with transaction.atomic():
        for guest in guests:
            payload = build_guest_move_payload(data, guest, new_room, tenant_id, with_identity=with_identity)

            if guest.room_id == new_room.id:
                _update_guest_in_place(guest, payload)
                continue

            # handle_guest_move() writes new_room.state back, so re-read it right before the
            # call: a stale array would drop flags (DoNotDisturb, MakeUpRoom, Reserved) that
            # make_stable_room_state does not restore — it only maintains Available/CheckedIn.
            new_room.refresh_from_db(fields=["state"])

            # handle_guest_move() saves the guest itself, so the title rides along with it
            if "title" in payload:
                guest.title = payload["title"]
            handle_guest_move(guest, payload)


def _update_guest_in_place(guest, payload):
    """Apply a datachange that leaves the guest in their current room.

    Most datachange traffic does not move anyone. Routing that through
    `handle_guest_move()` would treat one room row as both old and new and save it
    twice, re-running `full_clean()`, the RoomHistory lookup and the whole Room
    `post_save` chain (WS broadcast, device status push over RabbitMQ) — and re-dispatch
    cards for a device set that did not change.
    """
    changed = []

    for attr, key in (
        ("name", "first_name"),
        ("lastname", "last_name"),
        ("language", "language"),
        ("title", "title"),
        ("additional_info", "additional_info"),
    ):
        if key in payload and getattr(guest, attr) != payload[key]:
            setattr(guest, attr, payload[key])
            changed.append(attr)

    for attr, key in (("check_in", "check_in_date"), ("check_out", "check_out_date")):
        if key not in payload:
            continue
        value = datetime_to_unix(payload[key])
        if getattr(guest, attr) != value:
            setattr(guest, attr, value)
            changed.append(attr)

    if not changed:
        logger.info("datachange guest=%s: no field changed", guest.id)
        return

    logger.info("datachange guest=%s updated in place: %s", guest.id, changed)
    # No publish_guest_changes() here: the Guest post_save signal already does it
    guest.save()
