from celery import shared_task
from celery.utils.log import get_task_logger
from django.db.models import ExpressionWrapper, Func, Value, FloatField, F

from core.tests.aggregate_table_in_db import remove_duplicate_rows
from shuttle.models import TsKv

logger = get_task_logger(__name__)


@shared_task
def aggregate_table_db():
    logger.info("Task aggregating table")
    rounded_ts = ExpressionWrapper(
        Func(F("ts") / Value(30), function="FLOOR") * Value(30),
        output_field=FloatField(),
    )

    res = remove_duplicate_rows(
        TsKv.objects.annotate(ts_minute=rounded_ts),
        ["ts_minute", "entity_id", "key", "dbl_v"],
    )

    logger.info(res)
    logger.info("The aggregating table task successfully.")
