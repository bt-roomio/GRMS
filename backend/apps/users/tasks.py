import logging

from celery import shared_task
from django.core.management import call_command

logger = logging.getLogger(__name__)


@shared_task(name="users.tasks.flush_expired_tokens")
def flush_expired_tokens():
    """ """
    try:
        call_command("flushexpiredtokens")
    except Exception:
        logger.exception("flush expired tokens task failed")
        raise
