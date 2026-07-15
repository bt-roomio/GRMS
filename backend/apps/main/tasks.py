import time
from datetime import time as time_cls

from celery import shared_task
from celery.utils.log import get_task_logger
from django.db.models import Count, Q

from access_manager.tasks.send_rpc import send_rpc_request
from core.utils.helpers import safely_remove
from main.models import Guest, Room
from main.utils.access_context import get_guest_access_context

logger = get_task_logger(__name__)


@shared_task(name="main.tasks.auto_check_out")
def auto_check_out():
    logger.info("Auto check out task run.")
    six_hours_ago = time.time() - 21600  # 6 hours in seconds
    guests = Guest.objects.filter(is_active=True, auto_check_out=True, check_out__lte=six_hours_ago)
    guests_room_ids = set(guests.values_list("room_id", flat=True))

    access_context = get_guest_access_context(guests)  # ty: ignore
    cards = access_context.get("cards")
    if access_context.get("cards"):
        for device in access_context.get("devices"):  # ty: ignore
            _ = send_rpc_request(str(device.id), cards, 0)

    guests.update(is_active=False)

    rooms_with_active_guest_counts = Room.objects.annotate(
        active_guest_count=Count(
            "guests",
            filter=Q(guests__is_active=True, guests__auto_check_out=True, guests__check_out__lte=six_hours_ago),
        )
    ).filter(Q(active_guest_count__gt=0) | Q(id__in=guests_room_ids))

    for room in rooms_with_active_guest_counts:
        room.state = safely_remove(room.state, Room.CheckedIn)
        room.state.append(Room.Available)
        room.save(update_fields=["state"])

    logger.info("auto checkout task successfully finish.")


def _block_time_reached(g_settings, now_epoch):
    block_time = time_cls.fromisoformat(str(g_settings.get("guest_auto_block_time") or "12:00:00"))
    block_seconds = block_time.hour * 3600 + block_time.minute * 60 + block_time.second
    offset_hours = g_settings.get("timezone") or 0
    now_seconds = (now_epoch + offset_hours * 3600) % 86400
    return now_seconds >= block_seconds


@shared_task
def auto_block():
    logger.info("Auto block task run.")
    now_epoch = int(time.time())
    candidates = Guest.objects.filter(
        tenant__additional_info__general_settings__guest_auto_block=True,
        is_active=True,
        check_out__lte=time.time(),
        auto_check_out=False,
    ).select_related("tenant")
    print("guests selected: ", candidates)

    guest_ids = [
        guest.id
        for guest in candidates
        if _block_time_reached((guest.tenant.additional_info or {}).get("general_settings", {}), now_epoch)
    ]

    guests = Guest.objects.filter(id__in=guest_ids)
    access_context = get_guest_access_context(guests)  # ty: ignore
    guest_cards = access_context.get("guest_cards")
    cards = access_context.get("cards")
    if access_context.get("cards"):
        guest_cards.update(is_blocked=True)  # ty: ignore
        for device in access_context.get("devices"):  # ty: ignore
            _ = send_rpc_request(str(device.id), cards, 0)

    logger.info("auto block task successfully finish.")
