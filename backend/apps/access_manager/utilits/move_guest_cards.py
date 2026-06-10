import logging
from typing import Iterable, Optional, Union

from access_manager.models import GuestCard
from access_manager.tasks.send_rpc import send_rpc_request
from main.models import Guest
from main.utils.access_context import get_guest_access_context

logger = logging.getLogger(__name__)


def revoke_guest_cards(guests: Union[Guest, Iterable[Guest]], context: Optional[dict] = None) -> None:
    """Deactivate each guest's active cards on every device they currently access.

    Pass `context` (a `get_guest_access_context()` result) when the caller already
    captured it before mutating the guest; otherwise it's fetched here. Use this
    on checkout or any full access revoke — for room moves, use `move_guest_cards`.
    """
    if context is None:
        context = get_guest_access_context(guests)
    move_guest_cards(guests, context, {"devices": []})


def move_guest_cards(guests: Union[Guest, Iterable[Guest]], old_context: dict, new_context: dict) -> None:
    """Re-dispatch each guest's active cards when their accessible devices change.

    Deactivates cards on devices the guests no longer have access to and activates
    them on the newly accessible ones; devices present in both sets are left alone.

    `old_context` and `new_context` must be produced by
    `get_guest_access_context()` for the same `guests`,
    captured before and after the change (e.g. a room move). Only the "devices"
    key is read from each context.
    """
    if isinstance(guests, Guest):
        guests = [guests]

    old_device_ids = {str(d.id) for d in old_context["devices"]}
    new_device_ids = {str(d.id) for d in new_context["devices"]}
    remove_ids = old_device_ids - new_device_ids
    assign_ids = new_device_ids - old_device_ids

    if not remove_ids and not assign_ids:
        return

    cards_by_guest: dict = {}
    for gc in GuestCard.objects.filter(guest__in=guests, is_active=True).select_related("card"):
        cards_by_guest.setdefault(gc.guest_id, []).append(gc.card)

    for guest in guests:
        cards = cards_by_guest.get(guest.id, [])
        if not cards:
            continue
        guest_id = str(guest.id)
        for card in cards:
            is_pwd = bool(card.is_pwd)
            for device_id in remove_ids:
                send_rpc_request.delay(device_id, [card.number], 0, guest_id=guest_id, is_pwd=is_pwd)
            for device_id in assign_ids:
                send_rpc_request.delay(device_id, [card.number], 1, guest_id=guest_id, is_pwd=is_pwd)
