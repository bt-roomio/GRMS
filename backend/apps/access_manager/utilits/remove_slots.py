from typing import List


def remove_card_device_slots(cards: List[str], device):
    from access_manager.models import CardDeviceSlot

    if not device:
        return

    deleted_count, _ = CardDeviceSlot.objects.filter(card_number__in=cards, device=device).delete()

    return deleted_count
