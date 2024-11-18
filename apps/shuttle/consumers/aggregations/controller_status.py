from channels.db import database_sync_to_async
from django.db.models import Count

from main.models import Device, Room
from shuttle.utils.response import response


async def controller_status(cmd, user):
    result = response({}, cmd.get("cmdId"))
    status_controllers = await get_status_devices(user)
    status_rooms = await get_status_rooms(user)
    result["data"]["status_controllers"] = status_rooms
    result["data"]["count_active_rooms"] = status_controllers
    return result


@database_sync_to_async
def get_status_rooms(user):
    rooms = Room.objects.room_status(tenant=user.tenant)
    data = [room for room in rooms]
    return data


@database_sync_to_async
def get_status_devices(user):
    queryset = Device.objects.filter(tenant=user.tenant, room__isnull=False)
    queryset = queryset.values("status")
    queryset = queryset.annotate(count=Count("status"))
    return list(queryset)
