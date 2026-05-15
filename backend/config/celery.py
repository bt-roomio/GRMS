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
    Queue("low", routing_key="low"),
]
app.conf.task_default_queue = "default"
app.conf.task_default_routing_key = "default"

app.conf.task_routes = {
    "access_manager.tasks.sync_device.sync_devices_task": {"queue": "critical"},
    "main.tasks.auto_check_out": {"queue": "critical"},
    "main.tasks.auto_block": {"queue": "critical"},
    "shuttle.tasks.aggregate_table_ts_kv": {"queue": "low"},
    "shuttle.tasks.delete_old_logs": {"queue": "low"},
    "users.tasks.flush_expired_tokens": {"queue": "low"},
}

app.conf.update(
    task_soft_time_limit=300,
    task_time_limit=360,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_transport_options={
        "visibility_timeout": 43200,
        "retry_on_timeout": True,
    },
)
