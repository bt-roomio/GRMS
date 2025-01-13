from enum import Enum
import time

from shuttle.models import AttributeKv


def default_state():
    return [0]


class StateEnum(str, Enum):
    CHECKED_IN_STATUS = "CHECK IN STATUS"
    CHECKED_OUT_STATUS = "CHECK OUT STATUS"
    OCCUPANCY_STATUS = "OCCUPANCY STATUS"


table_status = {
    StateEnum.CHECKED_IN_STATUS: 1,
    StateEnum.CHECKED_OUT_STATUS: 6,
    StateEnum.OCCUPANCY_STATUS: 4,
}


def attribute_room_state(room, state: StateEnum, bool_v=True):
    from main.models import Device

    device = Device.objects.find_device_by_room(room)  # pyright: ignore

    if not device:
        return None, None, None

    AttributeKv.objects.update_or_create(
        entity=device,
        attribute_key=state.value,
        entity_type="DEVICE",
        attribute_type=AttributeKv.SHARED_SCOPE,
        defaults={"last_update_ts": time.time(), "bool_v": bool_v},
    )
    device_gateway = Device.objects.get_relation_or_gateway(device.id)  # pyright: ignore
    return ({state.value: table_status[state]}, str(device_gateway), device.name)
