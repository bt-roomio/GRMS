import time
from enum import Enum

from shuttle.models import AttributeKv


def default_state():
    return [0]


class StateEnum(str, Enum):
    RESERVED_STATUS = "Reserved"
    OCCUPANCY_STATUS = "OCCUPANCY STATUS"


def attribute_room_state(room, state: StateEnum, value=True):
    from main.models import Device

    device = Device.objects.find_device_by_room(room)  # pyright: ignore

    if not device:
        return None, None, None

    AttributeKv.objects.update_or_create(
        entity=device,
        attribute_key=state.value,
        entity_type="DEVICE",
        attribute_type=AttributeKv.SHARED_SCOPE,
        defaults={"last_update_ts": time.time(), "long_v": int(value)},
    )
    device_gateway = Device.objects.get_relation_or_gateway(device.id)  # pyright: ignore
    return ({state.value: int(value)}, str(device_gateway), device.name)
