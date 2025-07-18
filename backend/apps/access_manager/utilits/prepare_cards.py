import logging
from typing import List

from access_manager.models import CardDeviceSlot, StaffCard, Group, ALL_DAYS, WEEK_DAYS

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
    tenant_id = device.tenant_id
    for card_number in cards:
        if connect == 0 and device.device_profile.name.lower() == "default":
            connect = 1
        try:
            slot = find_or_assign_slot(card_number, device, connect)
            group = get_group(card_number, tenant_id) if not group else group
            group = group if group else None
        except CardDeviceSlot.DoesNotExist:
            continue
        card_data_params = data_params(card_number, group, connect, slot)
        card_data = {
            "cardNumber": card_data_params.get("cardNumber"),
            "access_group": card_data_params.get("access_group"),
            "start_time": card_data_params.get("start_time"),
            "end_time": card_data_params.get("end_time"),
            "weekdays": card_data_params.get("weekdays"),
            "slot_num": card_data_params.get("slot_num")
        }
        rpc_params.append(card_data)

    return rpc_params


def get_indexes_of_day(group: Group):
    values = [day_value for (day_value, _) in WEEK_DAYS]
    indexes = sorted([values.index(day) for day in group.week_days])
    return indexes


def get_group(card_number: str, tenant_id):
    try:
        staff_card = (
            StaffCard.objects
            .select_related("staff__group", "card")
            .filter(
                is_active=True,
                card__number=card_number,
                card__tenant_id=tenant_id,
                staff__is_active=True,
                staff__tenant_id=tenant_id,
                staff__group__isnull=False
            )
            .first()
        )
        print("staff_card", staff_card)

        group = staff_card.staff.group if staff_card.staff else None
        return group
    except Exception:
        return None


def data_params(card_number, group, connect, slot):
    params = {}
    card_number = str(card_number)
    if card_number == "00 00 00 00":
        return {"cardNumber": card_number, "access_group": "0", "start_time": "00:00", "end_time": "00:00",
                "weekdays": "0", "slot_num": "1"}
    access_group = str(group.group_type) if group and connect else str(int(connect))
    start_time = group.start_time.strftime("%H:%M") if group and group.start_time else "00:00"
    end_time = group.end_time.strftime("%H:%M") if group and group.end_time else "23:59"
    weekdays = ["1", "2", "3", "4", "5", "6", "7"] if not group or ALL_DAYS in group.week_days else get_indexes_of_day(
        group)
    slot_num = str(slot)
    params.update(
        {"cardNumber": card_number, "access_group": access_group, "start_time": start_time, "end_time": end_time,
         "weekdays": weekdays, "slot_num": slot_num})
    return params
