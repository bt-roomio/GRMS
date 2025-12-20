from django.db.models import Q

from access_manager.models import GuestCard
from main.models import Guest, Device, PublicSpace


def get_guest_relations(instance: Guest):
    guest_room = instance.room
    guests = [instance]
    guest_cards = GuestCard.objects.filter(guest=instance, is_active=True)
    blocked_guest_cards = GuestCard.objects.filter(guest=instance, is_blocked=True)
    blocked_cards = blocked_guest_cards.values_list("card__number", flat=True)
    cards = guest_cards.values_list("card__number", flat=True)
    guest_public_spaces = PublicSpace.objects.filter(guestpublicspace__guest=instance)

    devices = (
        Device.objects.filter(
            Q(room=guest_room) |
            Q(device_public_spaces__public_space__in=guest_public_spaces) |
            Q(device_public_spaces__public_space__room_type_public_spaces__room_type__room__guests__in=guests),
            is_active=True)
        .select_related("tenant")
        .distinct()
    )
    return guest_room, devices, guest_cards, cards, blocked_guest_cards, blocked_cards
