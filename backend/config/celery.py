import os

from celery import Celery
from kombu import Queue

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")


app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")


app.conf.task_queues = [
    Queue("critical", routing_key="critical"),
    Queue("default", routing_key="default"),
    # Отдельная очередь под высокочастотную WebSocket-публикацию из mq-async,
    # чтобы всплеск телеметрии не голодал остальные задачи default и наоборот.
    Queue("realtime", routing_key="realtime"),
    Queue("low", routing_key="low"),
]
app.conf.task_default_queue = "default"
app.conf.task_default_routing_key = "default"

app.conf.task_routes = {
    "access_manager.tasks.sync_device.sync_devices_task": {"queue": "critical"},
    "access_manager.tasks.sync_device.sync_device_card_group": {"queue": "critical"},
    "access_manager.tasks.room_card.manage_cards_for_room_task": {"queue": "critical"},
    "access_manager.tasks.public_space_card.manage_cards_for_public_space_task": {"queue": "critical"},
    "access_manager.tasks.send_rpc.send_rpc_request": {"queue": "critical"},
    "access_manager.tasks.unplug_card.unplug": {"queue": "critical"},
    "main.tasks.auto_check_out": {"queue": "critical"},
    "main.tasks.auto_block": {"queue": "critical"},
    # WebSocket-публикация и обновление активности устройств из mq-async.
    "shuttle.tasks.publish_updates_batch_task": {"queue": "realtime"},
    "shuttle.tasks.publish_updates_attribute_batch_task": {"queue": "realtime"},
    "shuttle.tasks.update_activity_devices_batch_task": {"queue": "realtime"},
    "shuttle.tasks.aggregate_table_ts_kv": {"queue": "low"},
    "shuttle.tasks.delete_old_logs": {"queue": "low"},
    "users.tasks.flush_expired_tokens": {"queue": "low"},
    "admin_panel.tasks.send_activation_email": {"queue": "low"},
    "mews.tasks.sync_access_tokens": {"queue": "low"},
}

app.conf.update(
    task_soft_time_limit=300,
    task_time_limit=360,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    # При обрыве соединения с брокером отменяем выполняемые acks_late-задачи и
    # переподключаемся чисто, вместо залипания consumer loop (это тот самый
    # CPendingDeprecationWarning в логах). Отменённые задачи будут повторно
    # доставлены после visibility_timeout.
    worker_cancel_long_running_tasks_on_connection_loss=True,
    # Продолжать переподключение к брокеру на старте воркера (в Celery 5.3+ это
    # вынесено из broker_connection_retry и без него сыплется предупреждение).
    broker_connection_retry_on_startup=True,
    broker_transport_options={
        "visibility_timeout": 43200,
        "retry_on_timeout": True,
        # Периодический PING, чтобы redis-транспорт замечал мёртвый сокет
        # (например, после рестарта redis-broker) и переподключался, а не висел.
        "health_check_interval": 10,
    },
)
