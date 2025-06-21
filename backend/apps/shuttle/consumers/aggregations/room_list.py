import json

from channels.db import database_sync_to_async

from core.utils.pagination import pagination
from core.utils.uuid_encode import UUIDEncoder
from main.models import Room
from main.serializers.room import RoomFilterParams, RoomSerializer
from shuttle.models import AttributeKv
from shuttle.utils.response import response


async def room_list(cmd, user):
    result = response({}, cmd.get("cmd_id"))
    try:
        filters = cmd.get("query", {}).get("filters", {})
        page_link = cmd.get("query", {}).get("page_link", {})
        params = await database_sync_to_async(RoomFilterParams.check)({**filters, **page_link})
        rooms = await get_rooms(params, user)
        result["data"] = rooms
    except Exception as err:
        result["error_code"] = 400
        result["error_msg"] = str(err)
    finally:
        return result


@database_sync_to_async
def get_rooms(params, user):
    queryset = Room.objects.list(  # pyright: ignore
        tenant=user.tenant,
        state=params.get("state"),
        status=params.get("status"),
        search_field=params.get("search_field"),
        search_value=params.get("search_value"),
        sort_by=params.get("sort_by"),
    )
    serializer = RoomSerializer(queryset, many=True)
    data = pagination(queryset, serializer, params.get("page"), params.get("size", 15))
    return json.loads(json.dumps(data, cls=UUIDEncoder))


@database_sync_to_async
def get_attributes(cmd, user):
    result = AttributeKv.objects.filter(
        entity_type=cmd.get("entityType"),
        entity_id=cmd.get("entityId"),
        attribute_type=cmd.get("scope"),
        entity__tenant=user.tenant,
    ).order_by("created_at")

    return list(result)
