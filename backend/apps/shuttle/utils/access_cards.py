from django.db.models import Q

from access_manager.utilits.dispatch_card_rpc import dispatch_card_rpc
from main.models import Device, Guest


def access_cards_via_card_numbers(guests, room, cards, access=1):
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
        dispatch_card_rpc(str(device.id), cards, access, source=Guest.SOURCE.MEWS)
