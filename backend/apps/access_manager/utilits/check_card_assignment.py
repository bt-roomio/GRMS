from typing import Dict, List
from access_manager.models import GuestCard, StaffCard


def get_card_assignments(cards: List[str], tenant_id: str, exclude_guest_id = None,
                         exclude_staff = None) -> Dict[str, str]:
    assignments: Dict[str, str] = {}

    guest_qs = GuestCard.objects.filter(
        is_active=True,
        card__number__in=cards,
        guest__tenant_id=tenant_id,
    )
    if exclude_guest_id:
        guest_qs = guest_qs.exclude(guest__id=exclude_guest_id)

    staff_qs = StaffCard.objects.filter(
        is_active=True,
        card__number__in=cards,
        staff__tenant_id=tenant_id,
    )
    if exclude_staff:
        staff_qs = staff_qs.exclude(staff=exclude_staff)

    for card_number in guest_qs.values_list("card__number", flat=True):
        assignments[card_number] = "guest"

    for card_number in staff_qs.values_list("card__number", flat=True):
        assignments[card_number] = "staff"

    return assignments
