import time

from shuttle.models import AttributeKv


def save_attributes(devices, available_fields, scope):
    attributes = {}
    fields = {"bool_v": None, "str_v": None, "long_v": None, "dbl_v": None, "json_v": None}

    for key, item in available_fields.items():
        field, value = item[0], item[1]
        fields[field] = value

        for device in devices:
            attribute_kv, _ = AttributeKv.objects.update_or_create(
                entity_id=device,
                attribute_type=scope,
                attribute_key=key,
                defaults={"entity_type": "DEVICE", **fields, "last_update_ts": int(time.time())},
            )
            attributes[str(device)] = attributes.get(str(device), {})
            attributes[str(device)][key] = value

    return attributes
