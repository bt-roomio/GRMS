from channels.db import database_sync_to_async
from django.db.models import Prefetch

from main.models import Device
from shuttle.models import AttributeKv
from shuttle.utils.camel_to_snake import camel_to_snake
from shuttle.utils.get_non_null_field import get_non_null_field
from shuttle.utils.response import response


@database_sync_to_async
def gateway_list(cmd, user):
    result = response({}, cmd.get("cmd_id"))

    entity_fields = cmd.get("query").get("entity_fields")
    entity_fields = [camel_to_snake(i.get("key")) for i in entity_fields]

    attributes = [i.get("key") for i in cmd.get("latest_cmd").get("keys") if i.get("type") == "ATTRIBUTE"]

    data = []
    attr = AttributeKv.objects.filter(attribute_key__in=attributes, attribute_type=AttributeKv.SHARED_SCOPE)
    devices = (
        Device.objects.is_active()  # pyright: ignore
        .filter(tenant=user.tenant)
        .prefetch_related(Prefetch(queryset=attr, lookup="attribute_kvs"))
        .filter(additional_info__gateway=True)
    )
    for device in devices:
        item = {"aggLatest": {}, "entityId": {"entityType": "DEVICE", "id": str(device.id)}, "latest": {}}
        fields = list(Device.objects.filter(id=device.id).values(*entity_fields))
        item["latest"]["ENTITY_FIELD"] = {
            key: {"ts": device.created_at, "value": value} for elem in fields for key, value in elem.items()
        }
        item["latest"]["ATTRIBUTE"] = {}
        for attribute in device.attribute_kvs.all():
            _, value = get_non_null_field(attribute)
            item["latest"]["ATTRIBUTE"][attribute.attribute_key] = {"ts": attribute.created_at, "value": value}
        data.append(item)
    result["data"] = data
    return result
