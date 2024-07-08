from channels.consumer import database_sync_to_async
from shuttle.models import AttributeKv
from shuttle.utils.get_non_null_field import get_non_null_field
from shuttle.utils.response import response


async def attribute_kv(cmd, user, send_json):
    result = response({}, cmd.get("cmdId"))
    latest_values = {}

    attributes = await get_attributes(cmd, user)
    for attribute in attributes:
        field, value = get_non_null_field(attribute)
        ts = attribute.created_at
        result["data"][attribute.attribute_key] = [[ts, value]]
        latest_values[attribute.attribute_key] = ts
        result["latestValues"] = latest_values

    await send_json(result)


@database_sync_to_async
def get_attributes(cmd, user):
    result = list(
        AttributeKv.objects.filter(
            entity_type=cmd.get("entityType"), entity_id=cmd.get("entityId"), attribute_type=cmd.get("scope")
        )
    )
    return result
