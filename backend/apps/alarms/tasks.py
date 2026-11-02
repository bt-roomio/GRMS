import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from alarms.models import Alarm
from alarms.notifications.dispatcher import dispatch
from alarms.services import engine
from alarms.telegram.exceptions import TelegramRateLimited

logger = logging.getLogger(__name__)

PURGE_BATCH_SIZE = 5000


@shared_task(name="alarms.tasks.evaluate_alarm_rules", ignore_result=True)
def evaluate_alarm_rules():
    if not settings.ALARMS_ENABLED:
        logger.info("Alarm evaluation skipped: ALARMS_ENABLED is off")
        return

    result = engine.evaluate()
    if result.created or result.cleared or result.escalated:
        logger.info("Alarm evaluation: %s", result)
    else:
        logger.info("Alarm evaluation: %s", result)


@shared_task(bind=True, name="alarms.tasks.dispatch_notifications", ignore_result=True, max_retries=5)
def dispatch_notifications(self):
    if not settings.ALARMS_ENABLED:
        return

    try:
        stats = dispatch()
    except TelegramRateLimited as exc:
        # Telegram told us exactly how long to wait; anything already sent is
        # marked, so the retry picks up where this left off.
        raise self.retry(countdown=exc.retry_after) from exc

    if stats["raised"] or stats["cleared"]:
        logger.info("Alarm notifications: %s", stats)


@shared_task(name="alarms.tasks.purge_alarms", ignore_result=True)
def purge_alarms():
    """
    The GRMS equivalent of TB's ``sql.ttl.alarms``.

    Only cleared alarms are ever removed — an open incident is never deleted by
    age, however old it is.
    """
    cutoff = timezone.now() - timedelta(days=settings.ALARMS_TTL_DAYS)
    total = 0

    while True:
        ids = list(
            Alarm.objects.filter(cleared=True, clear_ts__lt=cutoff).values_list("id", flat=True)[:PURGE_BATCH_SIZE]
        )
        if not ids:
            break
        deleted, _ = Alarm.objects.filter(id__in=ids).delete()
        total += deleted
        if len(ids) < PURGE_BATCH_SIZE:
            break

    if total:
        logger.info("Purged %s alarm row(s) cleared before %s", total, cutoff.date())
