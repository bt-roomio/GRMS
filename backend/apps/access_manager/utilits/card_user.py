from access_manager.models import StaffCard, GuestCard


def get_card_user(card_id):
    try:
        staff_card = StaffCard.objects.filter(card_id=card_id, is_active=True).first()
        if staff_card:
            staff = staff_card.staff
            return {"type": "staff", "name": staff.get_name()}

        guest_card = GuestCard.objects.filter(card_id=card_id, is_active=True).first()
        if guest_card:
            guest = guest_card.guest
            return {"type": "guest", "name": guest.get_name()}
        return {}
    except Exception:
        return {}