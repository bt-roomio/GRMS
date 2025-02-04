import time

from celery import shared_task
from celery.utils.log import get_task_logger
from django.db.models import Count, Q

from core.utils.helpers import safely_remove
from main.models import Guest, Room

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
