import json

from channels.db import database_sync_to_async
from django.shortcuts import get_object_or_404

from core.tests.uuid_encode import UUIDEncoder
from main.models import Room
from main.serializers.room import RoomSerializer
from shuttle.utils.response import response


async def room_detail(cmd, user):
    result = response({}, cmd.get("cmd_id"))
    try:
        query = cmd.get("query", {})
        rooms = await get_room(query.get("pk"), user)
        result["data"] = rooms
    except Exception as err:
        result["error_code"] = 400
        result["error_msg"] = str(err)
        return result
    return result


@database_sync_to_async
def get_room(pk, user):
    queryset = get_object_or_404(Room, id=pk, active=True, tenant_id=user.tenant_id)
    serializer = RoomSerializer(queryset, context={"detail": True})
    return json.loads(json.dumps(serializer.data, cls=UUIDEncoder))
