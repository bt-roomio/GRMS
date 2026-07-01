import logging

from access_manager.models import GuestCard, StaffCard
from access_manager.tasks.send_rpc import send_rpc_request
from main.utils.access_context import get_guest_access_context, get_staff_access_context

logger = logging.getLogger(__name__)


def disconnect_staff(card, card_num):
    staff_cards = StaffCard.objects.filter(card=card, is_active=True).select_related("staff", "staff__group")

    for staff_card in staff_cards:
        context = get_staff_access_context(staff_card.staff)
        all_removed = True
        for device in context.get("devices", []):
            result = send_rpc_request(str(device.id), [card_num], 0)  # sync
            if not result.get("success"):
                all_removed = False

        if all_removed:
            staff_card.is_active = False
            staff_card.save(update_fields=["is_active"])


def disconnect_guests(card, card_num):
    guest_cards = GuestCard.objects.filter(card=card, is_active=True).select_related("guest", "guest__room")
    guests = [gc.guest for gc in guest_cards]

    if not guests:
        return

    is_pwd = bool(card.is_pwd)
    context = get_guest_access_context(guests)
    for device in context["devices"]:
        send_rpc_request(str(device.id), [card_num], 0, is_pwd=is_pwd)
