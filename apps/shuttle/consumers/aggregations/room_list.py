import json
from uuid import UUID

from channels.db import database_sync_to_async
from django.core.serializers.json import DjangoJSONEncoder

from core.utils.pagination import pagination
from main.models import Room
from main.serializers.room import RoomFilterParams, RoomSerializer
from shuttle.models import AttributeKv
from shuttle.utils.response import response


class UUIDEncoder(DjangoJSONEncoder):
    def default(self, o):
        if isinstance(o, UUID):
            return str(o)
        return super().default(o)


async def room_list(cmd, user):
    result = response({}, cmd.get("cmdId"))
    try:
        params = RoomFilterParams.check(cmd.get("query", {}).get("filters"))
        rooms = await get_rooms(params, user)
        result["data"] = rooms
    except Exception as err:
        result["error_msg"] = str(err)
        return result
    return result


@database_sync_to_async
def get_rooms(params, user):
    queryset = Room.objects.list(
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
