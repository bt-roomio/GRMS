import time
from dataclasses import dataclass

from shuttle.models import AttributeKv


def default_state():
    return [0]


@dataclass
class AttributeConfig:
    attribute_key: str
    attribute_type: str
    value: int


def update_room_device_attributes(room, attributes: list[AttributeConfig]):
    from main.models import Device

    device = Device.objects.find_device_by_room(room)
    if not device:
        return

    for attr in attributes:
        AttributeKv.objects.update_or_create(
            entity=device,
            attribute_key=attr.attribute_key,
            entity_type="DEVICE",
            attribute_type=attr.attribute_type,
            defaults={"last_update_ts": time.time(), "long_v": attr.value},
        )
        device_gateway = Device.objects.get_relation_or_gateway(device.id)
        yield ({attr.attribute_key: attr.value}, attr.attribute_type, str(device_gateway), device.name)
