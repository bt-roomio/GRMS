from channels.db import database_sync_to_async
from django.db.models import Prefetch

from main.models import Device
from shuttle.models import AttributeKv
from shuttle.utils.get_non_null_field import get_non_null_field


@database_sync_to_async
def gateway_list(entity_fields, attributes):
    data = []
    attr = AttributeKv.objects.filter(attribute_key__in=attributes)
    devices = Device.objects.prefetch_related(Prefetch(queryset=attr, lookup="attribute_kvs")).filter(
        additional_info__gateway=True
    )
    for device in devices:
        item = {"aggLatest": {}, "entityId": {"entityType": "DEVICE", "id": str(device.id)}, "latest": {}}
        fields = list(Device.objects.filter(id=device.id).values(*entity_fields))
        item["latest"]["ENTITY_FIELD"] = {
            key: {"ts": device.created_at, "value": value} for elem in fields for key, value in elem.items()
        }
        item["latest"]["ATTRIBUTE"] = {}
        for attribute in device.attribute_kvs.all():
            field, value = get_non_null_field(attribute)
            item["latest"]["ATTRIBUTE"][attribute.attribute_key] = {"ts": attribute.created_at, "value": value}
        data.append(item)
    return data
