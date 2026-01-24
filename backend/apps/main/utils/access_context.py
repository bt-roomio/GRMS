from typing import List, Union
from django.db.models import Q, F

from access_manager.models import GuestCard, Staff, StaffCard, GroupRoom, GroupPublicSpace
from main.models import Guest, Device, PublicSpace


def get_guest_access_context(guests: Union[Guest, List[Guest]]) -> dict:
    if isinstance(guests, Guest):
        guests = [guests]

    guest_rooms = [guest.room for guest in guests if guest.room]
    guest_cards = GuestCard.objects.filter(guest__in=guests, is_active=True)
    blocked_guest_cards = GuestCard.objects.filter(guest__in=guests, is_blocked=True)
    blocked_cards = list(blocked_guest_cards.values_list("card__number", flat=True))
    cards = list(guest_cards.values_list("card__number", flat=True))
    guest_public_spaces = PublicSpace.objects.filter(guestpublicspace__guest__in=guests)

    door_lock_devices = Device.objects.filter(
        Q(room__in=guest_rooms),
        is_active=True,
        id=F('room__door_lock_device_id')
    ).select_related("tenant").distinct()

    public_space_devices = Device.objects.filter(
        Q(device_public_spaces__public_space__in=guest_public_spaces)
        | Q(device_public_spaces__public_space__room_type_public_spaces__room_type__room__guests__in=guests),
        is_active=True,
    ).select_related("tenant").distinct()

    if door_lock_devices.exists():
        devices = (door_lock_devices | public_space_devices).distinct()
    else:
        room_devices = Device.objects.filter(
            Q(room__in=guest_rooms),
            is_active=True,
        ).select_related("tenant").distinct()
        devices = (room_devices | public_space_devices).distinct()

    return {"guests": guests, "devices": devices, "guest_cards": guest_cards, "cards": cards,
            "blocked_guest_cards": blocked_guest_cards, "blocked_cards": blocked_cards}


def get_staff_access_context(staff: Staff) -> dict:
    if not staff.group:
        return {}

    group = staff.group
    staff_cards = StaffCard.objects.filter(staff=staff, is_active=True)
    cards = list(staff_cards.values_list("card__number", flat=True))

    group_rooms = GroupRoom.objects.filter(group=group).values_list("room", flat=True)
    group_public_spaces = GroupPublicSpace.objects.filter(group=group).values_list("public_space", flat=True)

    door_lock_devices = Device.objects.filter(
        Q(room__in=group_rooms),
        is_active=True,
        id=F('room__door_lock_device_id')
    ).distinct()

    public_space_devices = Device.objects.filter(
        Q(device_public_spaces__public_space__in=group_public_spaces),
        is_active=True,
    ).distinct()

    if door_lock_devices.exists():
        devices = (door_lock_devices | public_space_devices).distinct()
    else:
        room_devices = Device.objects.filter(
            Q(room__in=group_rooms),
            is_active=True,
        ).distinct()
        devices = (room_devices | public_space_devices).distinct()

    return {"staff": staff, "devices": devices, "staff_cards": staff_cards, "cards": cards}
