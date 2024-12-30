import logging

from celery import shared_task
from django.db import connection

logger = logging.getLogger("main")


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
