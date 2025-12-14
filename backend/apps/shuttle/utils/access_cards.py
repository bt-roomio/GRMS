from access_manager.models import GuestCard
from access_manager.tasks.send_rpc import send_rpc_request
from django.db.models import Q

from main.models import Device


def access_cards(guests, room, access=1):
    cards = GuestCard.objects.filter(guest__in=guests, is_active=True).values_list("card__number", flat=True)
    devices = (
        Device.objects.filter(
            Q(room__id=room.id)  # pyright: ignore
            | Q(device_public_spaces__public_space__room_type_public_spaces__room_type__room__guests__in=guests),
            is_active=True,
        )
        .select_related("tenant")
        .distinct()
    )
    for device in devices:
        send_rpc_request(str(device.id), cards, access)
        # not result.get("success") and deactivate_result.update({"success": False})  # pyright: ignore


def access_cards_via_card_numbers(guests, room, cards, access=1):
    # has_cards = GuestCard.objects.filter(number__in=cards, is_active=True).values_list("card__number", flat=True)
    # excluded_cards = filter(lambda card: card not in has_cards, cards)

    devices = (
        Device.objects.filter(
            Q(room_id=room)  # pyright: ignore
            | Q(device_public_spaces__public_space__room_type_public_spaces__room_type__room__guests__in=guests),
            is_active=True,
        )
        .select_related("tenant")
        .distinct()
    )
    for device in devices:
        send_rpc_request(str(device.id), cards, access)
        # not result.get("success") and deactivate_result.update({"success": False})  # pyright: ignore
