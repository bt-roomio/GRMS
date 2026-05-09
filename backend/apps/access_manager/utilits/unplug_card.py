import logging

from access_manager.models import GuestCard, NeedSyncDevice, StaffCard
from access_manager.tasks.send_rpc import send_rpc_request

from main.utils.access_context import get_guest_access_context, get_staff_access_context

logger = logging.getLogger(__name__)


def unplug(card):
    try:
        card_num = str(card.number)

        _disconnect_staff(card, card_num)
        _disconnect_guests(card, card_num)

        has_pending_sync = NeedSyncDevice.objects.filter(card=card, need_sync=True).exists()
        return not has_pending_sync

    except Exception as e:
        logger.error("Error disconnecting card %s: %s", card.id, str(e))
        return False


def _disconnect_staff(card, card_num):
    staff_cards = StaffCard.objects.filter(card=card, is_active=True).select_related("staff", "staff__group")

    for staff_card in staff_cards:
        context = get_staff_access_context(staff_card.staff)
        for device in context.get("devices", []):
            send_rpc_request.delay(str(device.id), [card_num], 0)

        staff_card.is_active = False
        staff_card.save(update_fields=["is_active"])


def _disconnect_guests(card, card_num):
    guest_cards = GuestCard.objects.filter(card=card, is_active=True).select_related("guest", "guest__room")
    guests = [gc.guest for gc in guest_cards]

    if not guests:
        return

    is_pwd = bool(card.is_pwd)
    context = get_guest_access_context(guests)
    for device in context["devices"]:
        send_rpc_request.delay(str(device.id), [card_num], 0, is_pwd=is_pwd)
