"""
Celery tasks for Mews integration
"""

import logging

from celery import shared_task
from django.core.management import call_command

logger = logging.getLogger(__name__)


@shared_task(name="mews.tasks.sync_reservations")
def sync_reservations():
    """
    Sync reservations from Mews for all active configurations
    Runs periodically via Celery Beat
    """
    try:
        logger.info("Starting Mews reservation sync task")
        call_command("mews_sync")
        logger.info("Mews reservation sync task completed successfully")
    except Exception as e:
        logger.error(f"Mews reservation sync task failed: {e}", exc_info=True)
        raise


@shared_task(name="mews.tasks.sync_access_tokens")
def sync_access_tokens():
    """
    Sync resource access tokens (key cards) from Mews for all active configurations
    Runs every minute via Celery Beat
    """
    try:
        logger.info("Starting Mews access tokens sync task")
        call_command("mews_access_tokens")
        logger.info("Mews access tokens sync task completed successfully")
    except Exception as e:
        logger.error(f"Mews access tokens sync task failed: {e}", exc_info=True)
        raise
