from access_manager.models import Card, GuestCard, NeedSyncDevice, StaffCard
from access_manager.utilits.need_sync import need_sync


def activate_guest_card(cards, device, guest):
    error_cards = []
    for card_number in cards:
        try:
            card, created = Card.objects.get_or_create(
                number=card_number,
                tenant_id=guest.tenant_id,
                defaults={"is_active": True}
            )
            if not created and not card.is_active:
                card.is_active = True
                card.save(update_fields=["is_active"])

            if GuestCard.objects.filter(guest=guest, card=card, is_active=True).exists():
                continue
            GuestCard.objects.create(guest=guest, card=card, is_active=True)
            NeedSyncDevice.objects.filter(card=card, device=device).update(need_sync=False)
        except Exception as e:
            need_sync(cards, device, 1, reason=f"Card activation failed: {e}")
            error_cards.append({"card_number": card_number, "error": str(e)})
    message = "Some cards are not activated."
    return {
        "success": error_cards == [],
        "error_cards": error_cards,
        "message": message if error_cards else "Successfully activated guest card.",
    }


def activate_staff_card(cards, staff, device):
    for card_number in cards:
        card, created = Card.objects.get_or_create(
            number=card_number,
            tenant_id=staff.tenant_id,
            defaults={"is_active": True}
        )
        if not created and not card.is_active:
            card.is_active = True
            card.save(update_fields=["is_active"])

        if StaffCard.objects.filter(staff=staff, card=card, is_active=True).exists():
            continue

        StaffCard.objects.create(staff=staff, card=card, is_active=True)
        NeedSyncDevice.objects.filter(card=card, device=device).update(need_sync=False)

    return {
        "success": True,
        "device": device.name,
        "message": "Successfully activated staff card.",
    }
