from enum import Enum
import time

from shuttle.models import AttributeKv


def default_state():
    return [0]


class StateEnum(str, Enum):
    CHECKED_IN_STATUS = "CHECK IN STATUS"
    CHECKED_OUT_STATUS = "CHECK OUT STATUS"
    OCCUPANCY_STATUS = "OCCUPANCY STATUS"


def attribute_room_state(room, state: StateEnum, bool_v=True):
    from main.models import Device

    device = Device.objects.find_device_by_room(room)

    if device:
        AttributeKv.objects.update_or_create(
            entity=device,
            attribute_key=state.value,
            entity_type="DEVICE",
            attribute_type=AttributeKv.SHARED_SCOPE,
            defaults={"last_update_ts": time.time(), "bool_v": bool_v},
        )
