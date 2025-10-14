from celery import shared_task

from core.monitoring.metrics import refresh_db_connection_metrics


@shared_task(ignore_result=True)
def update_db_metrics():
    refresh_db_connection_metrics()
