import logging
from typing import List

from access_manager.models import CardDeviceSlot, StaffCard, NeedSyncDevice, Group, ALL_DAYS, WEEK_DAYS

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


def prepare_cards(cards: List[str], device, connect, group: Group = None, sync: bool = False) -> List[dict]:
    rpc_params = []
    tenant_id = device.tenant_id
    for card_number in cards:
        connect = get_connect(card_number, device, connect)
        if connect == 0 and sync and device.device_profile.name.lower() == "default":
            continue
        elif connect == 0 and device.device_profile.name.lower() == "default":
            connect = 1
        try:
            slot = find_or_assign_slot(card_number, device, connect)
            group = get_group(card_number, tenant_id) if not group else group
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

        group = staff_card.staff.group if staff_card.staff else None
        return group
    except Exception:
        return None


def get_connect(card_number, device, connect_status):
    connect = connect_status
    try:
        obj = NeedSyncDevice.objects.filter(device_id=str(device.id), card__number=card_number, need_sync=True).first()
        print("obj.additional_info", obj.additional_info)
        connect = (obj.additional_info or {}).get("message_params", {}).get("access", None) if obj else connect
        return connect
    except Exception:
        return connect
