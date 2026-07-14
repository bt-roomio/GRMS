from django.db.models import Q

from access_manager.tasks.send_rpc import send_rpc_request
from main.models import Device


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
        send_rpc_request(str(device.id), cards, access)
