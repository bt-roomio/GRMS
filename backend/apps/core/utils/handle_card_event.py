from access_manager.models import StaffCard, GuestCard
from core.utils.str_to_dict import str_to_dict


def handle_card_event(value):
    try:
        value = str_to_dict(value)
        card_user = (
            StaffCard.objects.filter(card__number=value.get("card_uid"), is_active=True)
            .select_related("staff", "card")
            .values_list("id", "staff__id", "staff__first_name", "staff__last_name")
            .first()
        )
        user_type = "Staff"

        if not card_user:
            card_user = (
                GuestCard.objects.filter(card__number=value.get("card_uid"), is_active=True)
                .select_related("guest", "card")
                .values_list("id", "guest__id", "guest__name", "guest__lastname")
                .first()
            )
            user_type = "Guest"

        value.update({"user_type": user_type, "user_id": card_user[1], "user_name": f"{card_user[2]} {card_user[3]}"})
        return value
    except Exception:
        return value
