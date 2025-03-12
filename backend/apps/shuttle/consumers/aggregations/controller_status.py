from channels.db import database_sync_to_async
from django.db.models import Count

from main.models import Device, Room, RoomHistory
from shuttle.utils.response import response


async def controller_status(cmd, user):
    result = response({}, cmd.get("cmd_id"))
    try:
        count_active_rooms = await get_status_devices(user)
        status_controllers = await get_status_rooms(user)

        result["data"]["status_controllers"] = status_controllers
        result["data"]["count_active_rooms"] = count_active_rooms
    except Exception as err:
        result["error_code"] = 400
        result["error_msg"] = str(err)
    return result


@database_sync_to_async
def get_status_rooms(user):
    rooms = Room.objects.statuses(tenant=user.tenant)  # pyright: ignore
    rooms_history = RoomHistory.objects.yesterday_statuses(tenant=user.tenant)  # pyright: ignore
    data = merge_statuses(rooms, rooms_history)
    return data


@database_sync_to_async
def get_status_devices(user):
    queryset = Device.objects.is_active().filter(tenant=user.tenant, room__isnull=False)  # pyright: ignore
    queryset = queryset.values("status")
    queryset = queryset.annotate(count=Count("status"))
    return list(queryset)


def merge_statuses(today, yesterday):
    merged = {}

    for record in today:
        status = record["status"]
        merged[status] = {
            "status": status,
            "last_24_hour": record.get("today", 0),
            "diff_pervious_day": 0,
        }

    for record in yesterday:
        status = record["status"]
        if status in merged:
            merged[status]["diff_pervious_day"] = record.get("yesterday", 0)
        else:
            merged[status] = {
                "status": status,
                "last_24_hour": 0,
                "diff_pervious_day": record.get("yesterday", 0),
            }

    return list(merged.values())
