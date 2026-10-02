import os

from celery.schedules import crontab

from config.settings.components.base import TIME_ZONE

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_TASK_IGNORE_RESULT = True
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1")
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True
# Task events for Flower monitoring (otherwise the Tasks tab stays empty)
CELERY_WORKER_SEND_TASK_EVENTS = True
CELERY_TASK_SEND_SENT_EVENT = True

CELERY_BEAT_SCHEDULE = {
    "auto-checkout": {
        "task": "main.tasks.auto_check_out",
        "schedule": crontab(minute="*/5"),
    },
    "auto-block–guest": {
        "task": "main.tasks.auto_block",
        "schedule": 1800.0,
    },
    "sync_device": {
        "task": "access_manager.tasks.sync_device.sync_devices_task",
        "schedule": 300.0,
    },
    "clean_logs": {
        "task": "shuttle.tasks.delete_old_logs",
        "schedule": crontab(hour="0", minute="0"),
    },
    "update_db_metrics": {
        "task": "core.tasks.update_db_metrics",
        "schedule": 60.0,
    },
    "mews-sync": {
        "task": "mews.tasks.sync_reservations",
        "schedule": 60.0,
    },
    # "mews-access-tokens": { # TODO: comand not working, bacause need ServiceOrderIds
    #     "task": "mews.tasks.sync_access_tokens",
    #     "schedule": 60.0,
    # },
    "active-attribute-server-scope": {
        "task": "core.tasks.active_attribute_server_scope_task",
        "schedule": 10.0,  # Every 10 seconds
    },
    "aggregate-ts-kv": {
        "task": "shuttle.tasks.aggregate_table_ts_kv",
        "schedule": crontab(hour=3, minute=0),  # Every day at 03:00
    },
    "flush-expired-tokens": {
        "task": "users.tasks.flush_expired_tokens",
        "schedule": crontab(hour=3, minute=0),  # nightly at 3:00
    },
    "fleet-poll-peers": {
        "task": "fleet.tasks.poll_fleet_peers",
        "schedule": 60.0,
    },
}
