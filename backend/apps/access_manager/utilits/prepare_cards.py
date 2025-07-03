import logging
from typing import List

from access_manager.models import CardDeviceSlot, Group, ALL_DAYS, WEEK_DAYS

logger = logging.getLogger("main")


def find_or_assign_slot(card_number: str, device, connect) -> int:
    if not connect:
        try:
            slot = CardDeviceSlot.objects.get(card_number=card_number, device=device).slot
            return slot
        except CardDeviceSlot.DoesNotExist:
            logger.warning(f"Card {card_number} not found in device {device.id}")
            raise
    else:
        def get_next_slot():
            used_slots = set(CardDeviceSlot.objects.filter(device=device).values_list('slot', flat=True))
            current_slot = 1
            while current_slot in used_slots:
                current_slot += 1
            return current_slot

        card_slot, _ = CardDeviceSlot.objects.get_or_create(
            card_number=card_number,
            device=device,
            defaults={'slot': get_next_slot()}
        )
        return card_slot.slot


def prepare_cards(cards: List[str], device, connect, group: Group = None) -> List[dict]:
    rpc_params = []

    for card_number in cards:
        try:
            slot = find_or_assign_slot(card_number, device, connect)
        except CardDeviceSlot.DoesNotExist:
            continue

        card_data = {
            "cardNumber": card_number,
            "access_group": str(group.group_type) if group and connect else str(int(connect)),
            "start_time": group.start_time.strftime("%H:%M") if group and group.start_time else "00:00",
            "end_time": group.end_time.strftime("%H:%M") if group and group.end_time else "23:59",
            "weekdays": (
                ["1", "2", "3", "4", "5", "6", "7"] if not group or ALL_DAYS in group.week_days else get_indexes_of_day(
                    group)
            ),
            "slot_num": str(slot),
        }
        rpc_params.append(card_data)

    return rpc_params


def get_indexes_of_day(group: Group):
    values = [day_value for (day_value, _) in WEEK_DAYS]
    indices = sorted([values.index(day) for day in group.week_days])
    return indices
