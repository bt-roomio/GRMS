from shuttle.models import AttributeKv
from shuttle.utils.find_compatible_field import find_compatible_field


def save_attributes(devices, items, scope):
    attributes = {}
    instance = AttributeKv.objects.filter(entity__in=devices, attribute_key__in=items.keys(), attribute_type=scope)
    available_fields = find_compatible_field(items)
    for attr in instance:
        key = attr.attribute_key
        key_type = available_fields[key][0]
        value = available_fields[key][1]
        setattr(attr, key_type, value)
        attr.save()
        attributes[str(attr.entity_id)] = {key: value}

    return attributes
