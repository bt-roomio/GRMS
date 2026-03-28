import time
from enum import Enum

from shuttle.models import AttributeKv


def default_state():
    return [0]


class StateEnum(str, Enum):
    CHECK_IN_OUT = "Room reservation status"
    CHECK_IN_TRIGGER = "Check-in trigger"


def attribute_room_state(room, states: list[StateEnum], value=True):
    from main.models import Device

    device = Device.objects.find_device_by_room(room)  # pyright: ignore

    if not device:
        return None, None, None

    for state in states:
        AttributeKv.objects.update_or_create(
            entity=device,
            attribute_key=state.value,
            entity_type="DEVICE",
            attribute_type=(AttributeKv.SHARED_SCOPE if state == StateEnum.CHECK_IN_OUT else AttributeKv.CLIENT_SCOPE),
            defaults={"last_update_ts": time.time(), "long_v": int(value)},
        )
        device_gateway = Device.objects.get_relation_or_gateway(device.id)  # pyright: ignore
        yield ({state.value: int(value)}, str(device_gateway), device.name)
