from typing import List, Set
from django.db.models import Q
from uuid import UUID

from access_manager.models import StaffCard, GuestCard
from main.models import Device


def get_device_cards(device_id: UUID, tenant_id: UUID, cards: List = ()) -> List[str]:
    try:
        device = Device.objects.select_related('card', 'room').prefetch_related(
            'device_public_spaces__public_space'
        ).get(id=device_id, tenant_id=tenant_id)
    except Device.DoesNotExist:
        return []

    if device.device_profile.name != "default":
        return cards

    card_numbers: Set[str] = set()

    for card in cards:
        card_numbers.add(card)

    if device.card:
        card_numbers.add(device.card.number)

    staff_cards = StaffCard.objects.filter(
        Q(staff__group__group_room__room=device.room) |
        Q(staff__group__group_public_space__public_space__device_public_spaces__device=device),
        staff__is_active=True,
        is_active=True,
        card__tenant_id=tenant_id,
        staff__group__is_active=True,
        staff__group__tenant_id=tenant_id
    ).select_related('card').distinct()

    for staff_card in staff_cards:
        card_numbers.add(staff_card.card.number)

    guest_cards = GuestCard.objects.filter(
        Q(guest__room=device.room) |
        Q(guest__guestpublicspace__public_space__device_public_spaces__device=device) |
        Q(guest__room__type__room_type_public_spaces__public_space__device_public_spaces__device=device),
        is_active=True,
        card__tenant_id=tenant_id,
        guest__tenant_id=tenant_id
    ).select_related('card').distinct()

    for guest_card in guest_cards:
        card_numbers.add(guest_card.card.number)

    return list(card_numbers)
