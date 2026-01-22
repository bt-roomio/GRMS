import time

from celery import shared_task
from celery.utils.log import get_task_logger
from django.db.models import Count, Q

from access_manager.tasks.send_rpc import send_rpc_request
from core.utils.helpers import safely_remove
from main.models import Guest, Room
from main.utils.guest_relations import get_guest_relations

logger = get_task_logger(__name__)


@shared_task
def auto_check_out():
    logger.info("Auto check out task run.")
    guests = Guest.objects.filter(is_active=True, auto_check_out=True, check_out__lte=time.time())
    guests_room_ids = set(guests.values_list("room_id", flat=True))
    guests.update(is_active=False)

    rooms_with_active_guest_counts = Room.objects.annotate(
        active_guest_count=Count(
            "guests",
            filter=Q(guests__is_active=True, guests__auto_check_out=True, guests__check_out__lte=time.time()),
        )
    ).filter(Q(active_guest_count__gt=0) | Q(id__in=guests_room_ids))

    for room in rooms_with_active_guest_counts:
        room.state = safely_remove(room.state, Room.CheckedIn)
        room.state.append(Room.Available)
        room.save(update_fields=["state"])

    logger.info("auto checkout task successfully finish.")


@shared_task
def auto_block():
    logger.info("Auto block task run.")
    guests = Guest.objects.filter(tenant__additional_info__general_settings__guest_auto_block=True, is_active=True,
                                  check_out__lte=time.time())
    for guest in guests:
        _, devices, guest_cards, cards, _, _ = get_guest_relations(guest)
        if cards:
            guest_cards.update(is_blocked=True)
            for device in devices:
                _ = send_rpc_request(str(device.id), cards, 0)

    logger.info("auto block task successfully finish.")
