import time

from celery import shared_task
from celery.utils.log import get_task_logger
from django.db.models import Prefetch

from main.models import Guest, Room

logger = get_task_logger(__name__)


@shared_task
def auto_check_out():
    logger.info("The sample task just ran.")
    guests = Guest.objects.filter(is_active=True, auto_check_out=True, check_out__lte=time.time())
    rooms = Room.objects.prefetch_related(Prefetch("guests", queryset=guests))

    for room in rooms:
        for guest in room.guests.all():
            if len(Room.objects.filter(id=guest.room_id)) == 1:
                room.state = Room.Available
                room.save()

            guest.is_active = False
            guest.save()

    logger.info("The sample task successfully.")
