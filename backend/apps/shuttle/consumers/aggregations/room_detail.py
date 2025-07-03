import json

from channels.db import database_sync_to_async
from django.db.models import Count, Q

from core.utils.uuid_encode import UUIDEncoder
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
    query = Room.objects.filter(id=pk, active=True, tenant_id=user.tenant_id)
    if not query:
        raise Exception("Room not found")

    query = query.prefetch_related("devices__ts_kvs_latest__key", "type")

    query = query.annotate(
        count_online_devices=Count("devices", filter=Q(Q(devices__status=True) & Q(devices__is_active=True)))
    )
    query = query.annotate(count_devices=Count("devices", filter=Q(devices__is_active=True)))
    instance = query.first()

    serializer = RoomSerializer(instance, context={"detail": True})
    return json.loads(json.dumps(serializer.data, cls=UUIDEncoder))
