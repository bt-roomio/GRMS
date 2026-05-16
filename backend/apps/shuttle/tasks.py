import logging
from datetime import timedelta

from celery import shared_task
from django.db import connection
from django.db.models import Q
from django.utils import timezone

from core.management.mq.state_device import update_activity_device
from shuttle.models import TsKv, TsKvDictionary
from shuttle.services.attribute_kv import publish_updates_attribute_batch
from shuttle.services.ts_kv_latest import publish_updates_batch

logger = logging.getLogger(__name__)

DEDUP_BATCH_SIZE = 10_000


def deduplicate_ts_kv(key: int | None = None, entity_id: str | None = None):
    """Deduplicate shuttle_ts_kv by 30-second windows using ROW_NUMBER() (TimescaleDB chunk-aware).

    Args:
        key: Optional key filter (TsKvDictionary.key_id) for targeted deduplication.
        entity_id: Optional entity_id filter (Device UUID) for targeted deduplication.
    """
    extra_filter = ""
    if key is not None:
        extra_filter += " AND key = %(key)s"
    if entity_id is not None:
        extra_filter += " AND entity_id = %(entity_id)s"

    filter_params = {"key": key, "entity_id": entity_id}
    logger.info(f"Dedup ts_kv: key={key}, entity_id={entity_id}")

    with connection.cursor() as cursor:
        cursor.execute("SET statement_timeout = 0")

        cursor.execute(
            """
            SELECT range_start, range_end
            FROM timescaledb_information.chunks
            WHERE hypertable_name = 'shuttle_ts_kv'
            ORDER BY range_start ASC
            """
        )
        chunks = cursor.fetchall()
        logger.info(f"Dedup ts_kv: total chunks={len(chunks)}")

        total_deleted = 0

        for chunk_idx, (chunk_start, chunk_end) in enumerate(chunks, 1):
            chunk_deleted = 0

            while True:
                cursor.execute(
                    f"""
                    WITH ranked AS (
                        SELECT ts, entity_id, key,
                               ROW_NUMBER() OVER (
                                   PARTITION BY
                                       key,
                                       entity_id,
                                       bool_v,
                                       str_v,
                                       long_v,
                                       dbl_v,
                                       json_v,
                                       DATE_TRUNC('minute', ts)
                                           + INTERVAL '30 seconds' * FLOOR(EXTRACT(SECOND FROM ts) / 30)
                                   ORDER BY ts DESC
                               ) AS rn
                        FROM shuttle_ts_kv
                        WHERE ts >= %(chunk_start)s AND ts < %(chunk_end)s
                        {extra_filter}
                    )
                    DELETE FROM shuttle_ts_kv
                    WHERE (ts, entity_id, key) IN (
                        SELECT ts, entity_id, key
                        FROM ranked
                        WHERE rn > 1
                        LIMIT %(batch_size)s
                    )
                    AND ts >= %(chunk_start)s AND ts < %(chunk_end)s
                    {extra_filter}
                    """,
                    {
                        "chunk_start": chunk_start,
                        "chunk_end": chunk_end,
                        "batch_size": DEDUP_BATCH_SIZE,
                        **filter_params,
                    },
                )

                deleted = cursor.rowcount
                chunk_deleted += deleted
                total_deleted += deleted

                if deleted < DEDUP_BATCH_SIZE:
                    break

            if chunk_deleted > 0:
                logger.info(
                    f"Dedup ts_kv [{chunk_idx}/{len(chunks)}] {chunk_start.date()} "
                    f"| chunk_deleted={chunk_deleted} | total={total_deleted}"
                )

    logger.info(f"Dedup ts_kv done. Total deleted: {total_deleted}")
    return total_deleted


@shared_task
def aggregate_table_ts_kv():
    logger.info("Task aggregating table shuttle_ts_kv")
    deleted = deduplicate_ts_kv()
    logger.info(f"The aggregating table task completed. Deleted: {deleted}")


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
def update_activity_devices_batch_task(device_ids: list, connected=True):
    for device_id in device_ids:
        update_activity_device(device_id, connected)


@shared_task
def publish_updates_batch_task(updates_by_device: dict[str, list[dict]]):
    publish_updates_batch(updates_by_device)


@shared_task
def publish_updates_attribute_batch_task(updates_by_device: dict[str, list[dict]]):
    """
    Асинхронная отправка обновлений атрибутов через WebSocket.
    Уменьшает блокировку RabbitMQ воркеров.
    """
    publish_updates_attribute_batch(updates_by_device)
