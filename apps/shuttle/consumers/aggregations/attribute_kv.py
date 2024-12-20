from channels.consumer import database_sync_to_async

from shuttle.models import AttributeKv
from shuttle.utils.get_non_null_field import get_non_null_field
from shuttle.utils.response import response


async def attribute_kv(cmd, user):
    result = response({}, cmd.get("cmd_id"))
    latest_values = {}

    attributes = await get_attributes(cmd, user)
    for attribute in attributes:
        _, value = get_non_null_field(attribute)
        ts = attribute.last_update_ts
        result["data"][attribute.attribute_key] = [[ts, value]]
        latest_values[attribute.attribute_key] = ts
        result["latestValues"] = latest_values

    return result


@database_sync_to_async
def get_attributes(cmd, user):
    result = AttributeKv.objects.filter(
        entity_type=cmd.get("entity_type"),
        entity_id=cmd.get("entity_id"),
        attribute_type=cmd.get("scope"),
        entity__tenant=user.tenant,
    ).order_by("created_at")

    return list(result)
