import logging

from access_manager.models import GuestCard
from core.management.mq.fias.exceptions import LookupFailure
from core.management.mq.fias.utils.guests import resolve_guests_for_keydelete
from core.management.mq.fias.utils.rpc import (
    send_card_operation_confirmation,
    send_rpc_to_guest_devices,
)

logger = logging.getLogger(__name__)


def handle_keydelete(data, device):
    operation_id = data["operationId"]
    tenant_id = device.get("tenant_id")
    room_name = data.get("roomName")
    reservation_number = data.get("reservationNumber")

    try:
        guests = resolve_guests_for_keydelete(tenant_id, room_name, reservation_number)
    except LookupFailure as e:
        logger.warning(
            "keydelete lookup failed operationId=%s room=%s reservation=%s: %s",
            operation_id,
            room_name,
            reservation_number,
            e,
        )
        send_card_operation_confirmation(
            device, operation_id, status="OK", text="No cards to delete"
        )
        return

    guest_cards = list(
        GuestCard.objects.filter(guest__in=guests, is_active=True).select_related(
            "guest", "card"
        )
    )
    if not guest_cards:
        send_card_operation_confirmation(
            device, operation_id, status="OK", text="No assigned cards to delete"
        )
        return

    logger.info(
        "keydelete operationId=%s room=%s cards=%d",
        operation_id,
        room_name,
        len(guest_cards),
    )
    _revoke_guest_cards(guest_cards)

    send_card_operation_confirmation(
        device, operation_id, status="OK", text="Delete request accepted"
    )


def _revoke_guest_cards(guest_cards):
    for gc in guest_cards:
        uid = gc.card.number
        success, text = send_rpc_to_guest_devices(gc.guest, uid, access=0)
        if not success:
            logger.warning(
                "keydelete: failed to delete card %s for guest %s: %s",
                uid,
                gc.guest.id,
                text,
            )
