import json
from uuid import UUID

from channels.db import database_sync_to_async
from django.core.serializers.json import DjangoJSONEncoder

from core.utils.pagination import pagination
from main.models import Guest
from main.serializers.guest import GuestFilterParams, GuestSerializer
from shuttle.utils.response import response


class UUIDEncoder(DjangoJSONEncoder):
    def default(self, o):
        if isinstance(o, UUID):
            return str(o)
        return super().default(o)


async def guest_list(cmd, user):
    result = response({}, cmd.get("cmd_id"))
    try:
        filters = cmd.get("query", {}).get("filters", {})
        page_link = cmd.get("query", {}).get("page_link", {})
        params = await database_sync_to_async(GuestFilterParams.check)({**filters, **page_link})
        rooms = await get_guests(params, user)
        result["data"] = rooms
    except Exception as err:
        result["error_msg"] = str(err)
        return result
    return result


@database_sync_to_async
def get_guests(params, user):
    queryset = Guest.objects.list(tenant_id=user.tenant_id, room=params.get("room"))
    serializer = GuestSerializer(queryset, many=True)
    data = pagination(queryset, serializer, params.get("page"), params.get("size", 15))
    return json.loads(json.dumps(data, cls=UUIDEncoder))
