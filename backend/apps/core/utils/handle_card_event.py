from access_manager.models import GuestCard, StaffCard
from django.db.models import DurationField, ExpressionWrapper, F
from django.db.models.functions import Abs

from core.utils.str_to_dict import str_to_dict


def handle_card_event(data):
    """
    Processes a list of card event messages by identifying the associated user
    (Staff or Guest) based on the card UID and event timestamp. It adds user
    details (type, ID, and name) to each message's value field. Falls back to
    "Unknown" if no match is found.
    """
    try:
        for message in data:
            value = message.get("value")
            value = str_to_dict(value)

            event_timestamp_init = value.get("event_ts")
            card_uid = value.get("card_uid")

            if not card_uid:
                continue

            event_timestamp = event_timestamp_init * 1000

            staff_card = (
                StaffCard.objects.filter(card__number=card_uid, is_active=True, created_at__lte=event_timestamp_init)
                .select_related("staff", "card")
                .annotate(
                    time_diff=ExpressionWrapper(
                        Abs(F("created_at") - event_timestamp_init), output_field=DurationField()
                    )
                )
                .order_by("time_diff")
                .values("id", "staff__id", "staff__first_name", "staff__last_name", "time_diff")
                .first()
            )

            guest_card = (
                GuestCard.objects.filter(card__number=card_uid, is_active=True, created_at__lte=event_timestamp)
                .select_related("guest", "card")
                .annotate(
                    time_diff=ExpressionWrapper(Abs(F("created_at") - event_timestamp), output_field=DurationField())
                )
                .order_by("time_diff")
                .values("id", "guest__id", "guest__name", "guest__lastname", "time_diff")
                .first()
            )

            user_type = "Unknown"
            if staff_card and guest_card:
                if staff_card["time_diff"] <= guest_card["time_diff"]:
                    card_user = staff_card
                    user_type = "Staff"
                else:
                    card_user = guest_card
                    user_type = "Guest"
            elif staff_card:
                card_user = staff_card
                user_type = "Staff"
            elif guest_card:
                card_user = guest_card
                user_type = "Guest"
            else:
                card_user = None

            if card_user:
                if user_type == "Staff":
                    value.update(
                        {
                            "user_type": user_type,
                            "user_id": card_user.get("staff__id"),
                            "user_name": f"{card_user.get('staff__first_name')} {card_user.get('staff__last_name')}",
                        }
                    )
                elif user_type == "Guest":
                    value.update(
                        {
                            "user_type": user_type,
                            "user_id": card_user.get("guest__id"),
                            "user_name": f"{card_user.get('guest__name')} {card_user.get('guest__lastname')}",
                        }
                    )
            else:
                value.update(
                    {
                        "user_type": "Unknown",
                        "user_id": None,
                        "user_name": "Unknown User",
                    }
                )

            message.update({"value": value})
        return data
    except Exception:
        return data
