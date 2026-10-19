import os

from celery import Celery
from celery import signals as celery_signals
from kombu import Queue

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")


app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@celery_signals.setup_logging.connect
def configure_celery_logging(**kwargs):
    """Hand Celery the Django logging config instead of its built-in one.

    Without a receiver for this signal Celery considers logging its own: with
    worker_hijack_root_logger (on by default) it clears the handlers of the
    ``celery`` logger and attaches a handler only to root. But settings.LOGGING
    sets ``propagate: False`` for ``celery``, so after such "configuration"
    beat and worker records go nowhere, and the log looks empty.
    """
    from logging.config import dictConfig

    from django.conf import settings

    dictConfig(settings.LOGGING)


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")


app.conf.task_queues = [
    Queue("critical", routing_key="critical"),
    Queue("default", routing_key="default"),
    # A dedicated queue for high-frequency WebSocket publishing from mq-async,
    # so a telemetry burst doesn't starve the other default tasks and vice versa.
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
    "fleet.tasks.run_fleet_job": {"queue": "critical"},
    "main.tasks.auto_check_out": {"queue": "critical"},
    "main.tasks.auto_block": {"queue": "critical"},
    # Only celery-low is mounted with docker.sock and deploy/; -c 1 rules out races over env files.
    "main.tasks.provision_nodered_task": {"queue": "low"},
    "main.tasks.deprovision_nodered_task": {"queue": "low"},
    # WebSocket publishing and device activity updates from mq-async.
    "shuttle.tasks.publish_updates_batch_task": {"queue": "realtime"},
    "shuttle.tasks.publish_updates_attribute_batch_task": {"queue": "realtime"},
    "shuttle.tasks.update_activity_devices_batch_task": {"queue": "realtime"},
    "shuttle.tasks.aggregate_table_ts_kv": {"queue": "low"},
    "shuttle.tasks.delete_old_logs": {"queue": "low"},
    "users.tasks.flush_expired_tokens": {"queue": "low"},
    "admin_panel.tasks.send_activation_email": {"queue": "low"},
    "mews.tasks.sync_access_tokens": {"queue": "low"},
    "alarms.tasks.evaluate_alarm_rules": {"queue": "default"},
    "alarms.tasks.dispatch_notifications": {"queue": "low"},
    "alarms.tasks.purge_alarms": {"queue": "low"},
}

app.conf.update(
    task_soft_time_limit=300,
    task_time_limit=360,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    # When the broker connection drops, cancel running acks_late tasks and
    # reconnect cleanly instead of the consumer loop getting stuck (that is the
    # CPendingDeprecationWarning in the logs). Cancelled tasks will be redelivered
    # after visibility_timeout.
    worker_cancel_long_running_tasks_on_connection_loss=True,
    # Keep retrying the broker connection on worker startup (in Celery 5.3+ this
    # was split out of broker_connection_retry, and without it a warning is emitted).
    broker_connection_retry_on_startup=True,
    broker_transport_options={
        "visibility_timeout": 43200,
        "retry_on_timeout": True,
        # Periodic PING so the redis transport notices a dead socket
        # (e.g. after a redis-broker restart) and reconnects instead of hanging.
        "health_check_interval": 10,
    },
)
