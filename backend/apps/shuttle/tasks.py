from celery import shared_task

from core.management.mq.handlers.state_device import update_activity_devices_batch
from shuttle.services.attribute_kv import publish_updates_attribute_batch
from shuttle.services.ts_kv_latest import publish_updates_batch
from shuttle.services.ts_kv_purge import purge_ts_kv_keys

# Stops well before the 300s soft time limit; what is left goes to the next night.
PURGE_TIME_BUDGET = 240


@shared_task
def update_activity_devices_batch_task(device_ids: list, connected=True):
    update_activity_devices_batch(device_ids, connected)


@shared_task
def publish_updates_batch_task(updates_by_device: dict[str, list[dict]]):
    publish_updates_batch(updates_by_device)


@shared_task
def publish_updates_attribute_batch_task(updates_by_device: dict[str, list[dict]]):
    """
    Asynchronously send attribute updates over WebSocket.
    Reduces blocking of RabbitMQ workers.
    """
    publish_updates_attribute_batch(updates_by_device)


@shared_task(ignore_result=True)
def purge_ts_kv_keys_task():
    purge_ts_kv_keys(time_budget=PURGE_TIME_BUDGET)
