from access_manager.models import GuestCard, NeedSyncDevice, CardDeviceSlot, StaffCard


def deactivate_guest_card(cards, device, sync):
    error_cards = []
    for card in cards:
        try:
            instance = GuestCard.objects.get(guest__room=device.room, card__number=card, is_active=True)
            instance.is_active = False
            instance.is_blocked = False
            instance.save(update_fields=["is_active", "is_blocked"])
            CardDeviceSlot.objects.filter(card_number=card, device=device).delete()
            NeedSyncDevice.objects.filter(card__number=card, device=device).update(need_sync=False)
        except Exception:
            not sync and error_cards.append(card)
    message = "Some cards are not deactivated."
    return {
        "success": error_cards == [],
        "error_cards": error_cards,
        "message": message if error_cards else "Cards are deactivated.",
    }


def deactivate_staff_card(staff, staff_card=None):
    try:
        if staff_card:
            StaffCard.objects.filter(id=staff_card, is_active=True).update(is_active=False)
        else:
            StaffCard.objects.filter(staff=staff, is_active=True).update(is_active=False)
        return {"success": True, "message": "Card is deactivated."}
    except Exception:
        return {"success": False, "message": "Could not disconnect card, please try again !"}
