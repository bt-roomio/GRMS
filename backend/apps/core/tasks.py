import logging

from celery import shared_task
from django.core.management import call_command

from core.monitoring.metrics import refresh_db_connection_metrics

logger = logging.getLogger(__name__)


@shared_task(name="core.tasks.update_db_metrics", ignore_result=True)
def update_db_metrics():
    refresh_db_connection_metrics()


# task for active_attribute_server_scope.py
@shared_task(name="core.tasks.active_attribute_server_scope_task")
def active_attribute_server_scope_task():
    """
    Periodic task to check and update gateway device activity status.

    This task runs the active_attribute_server_scope management command,
    which checks the lastActivityTime of gateway devices and marks inactive
    devices (>60s without activity) as inactive. For gateway devices, it also
    cascades the deactivation to all related devices.

    Scheduled to run every 10 seconds via Celery Beat.

    Raises:
        Exception: Re-raises any exception that occurs during command execution
                  after logging the error.
    """
    try:
        logger.info("Starting Active Attribute SERVER_SCOPE task")
        call_command("active_attribute_server_scope")
        logger.info("Active Attribute SERVER_SCOPE task completed successfully")
    except Exception as e:
        logger.error(f"Active Attribute SERVER_SCOPE task failed: {e}", exc_info=True)
        raise
