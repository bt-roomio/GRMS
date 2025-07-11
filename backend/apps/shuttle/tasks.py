import logging
from datetime import timedelta

from celery import shared_task
from django.db import connection
from django.db.models import Q
from django.utils import timezone

from core.management.mq.state_device import update_activity_device
from shuttle.models import TsKv, TsKvDictionary
from shuttle.services.ts_kv_latest import publish_updates_batch

logger = logging.getLogger(__name__)


@shared_task
def aggregate_table_ts_kv():
    logger.info("Task aggregating table shuttle_ts_kv")
    diff_time = 30

    with connection.cursor() as cursor:
        cursor.execute(
            f"""
                    WITH ranked_duplicates AS (
                        SELECT entity_id,
                               key,
                               ts,
                               dbl_v,
                               ROW_NUMBER() OVER (PARTITION BY entity_id, key, FLOOR(ts / {diff_time}) ORDER BY ABS(dbl_v)) AS row_num
                        FROM shuttle_ts_kv
                        WHERE dbl_v IS NOT NULL
                    )
                    DELETE FROM shuttle_ts_kv
                    WHERE (entity_id, key, ts) IN (
                        SELECT entity_id, key, ts
                        FROM ranked_duplicates
                        WHERE row_num > 1
                    );
                    """
        )
        logger.info(cursor.rowcount, "records deleted")
    logger.info("The aggregating table task successfully.")


@shared_task
def delete_old_logs():
    keys = TsKvDictionary.objects.filter(
        Q(key__endswith="_LOGS") | Q(key__contains="Events") | Q(key__contains="ERRORS")
    )
    logger.info(f"Keys: {", ".join(keys.values_list('key', flat=True))}")
    logs = TsKv.objects.filter(key__in=keys, ts__lte=(timezone.now() - timedelta(days=7)))
    logger.info(f" {logs.delete()[0]} log(s) deleted!")


@shared_task
def update_activity_device_task(device_id, connected=True):
    update_activity_device(device_id, connected)


@shared_task
def publish_updates_batch_task(updates_by_device: dict[str, list[dict]]):
    publish_updates_batch(updates_by_device)
