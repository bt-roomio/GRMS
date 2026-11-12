import os

from config.settings.components import env_bool

_LOG_LEVEL = os.getenv("DJANGO_LOG_LEVEL", "WARNING").upper()
_LOG_FORMATTER = os.getenv("DJANGO_LOG_FORMATTER", "simple")
_LOG_SQL = env_bool("DJANGO_LOG_SQL", "false")

# Third-party libraries that are chatty at INFO (per connection/message/request).
# They are capped at WARNING regardless of DJANGO_LOG_LEVEL.
_QUIET_LOGGERS = (
    "aio_pika",
    "aiormq",
    "amqp",
    "asyncssh",
    # Per-task "received"/"succeeded" lines; failures are logged at ERROR anyway.
    # The rest of the celery tree (beat "Sending due task", worker "ready") follows
    # DJANGO_LOG_LEVEL.
    "celery.app.trace",
    "celery.worker.strategy",
    "engineio",
    "kombu",
    "pika",
    "socketio",
    "urllib3",
    "websocket",
    "websockets",
)

# All logs go to stdout/stderr — rotation and retention are handled by Docker
# (x-logging in deploy/docker-compose.yml: json-file, max-size 50m, max-file 5).
# File handlers are deliberately unused: RotatingFileHandler is not
# multiprocess-safe with GUNICORN_WORKERS > 1, and writing inside the container
# without a volume is lost on redeploy.
#
# Single handler on the root logger: every logger (project apps via
# getLogger(__name__), third-party libraries) propagates up to it, so a new app
# needs no entry here. Loggers below only adjust levels — giving them their own
# handler as well would print each record twice.
#
# Celery workers/beat apply this same config (core.log.celery), so their -l flag
# does not affect logging; DJANGO_LOG_LEVEL is the only knob.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    # {name} is present in every text format: all subsystems log into a single
    # stdout, and the logger name is the only way to tell security/hoteza/… apart
    # when reading them (`docker logs django | grep ' security '`).
    # {ctx} is "[request_id=… task_id=… tenant_id=…] " or empty (core.log.filters).
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {name} {module}:{lineno} {process:d} {thread:d} {ctx}{message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {asctime} {name} {ctx}{message}",
            "style": "{",
        },
        "verbose_with_location": {
            "format": "[{levelname}] {asctime} [{name}] {pathname}:{lineno} | {ctx}{message}",
            "style": "{",
        },
        "json": {
            "()": "core.log.formatters.JSONFormatter",
        },
    },
    "filters": {
        "context": {
            "()": "core.log.filters.ContextFilter",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": _LOG_FORMATTER,
            "filters": ["context"],
        },
    },
    "root": {
        "handlers": ["console"],
        "level": _LOG_LEVEL,
    },
    "loggers": {
        # Listed explicitly so dictConfig strips the handlers Django's
        # DEFAULT_LOGGING attached to them (console with require_debug_true,
        # mail_admins); otherwise records would be printed twice under DEBUG.
        "django": {
            "handlers": [],
            "level": _LOG_LEVEL,
        },
        # 4xx are routine (expired tokens, validation); only 5xx are logged.
        "django.request": {
            "level": "ERROR",
        },
        **({"django.db.backends": {"level": "DEBUG"}} if _LOG_SQL else {}),
        # INFO is set explicitly instead of _LOG_LEVEL: lockout and successful
        # login events are always needed, regardless of overall log verbosity.
        "security": {
            "level": "INFO",
        },
        # Hoteza views/serializers log whole webhook payloads (guest PII) at INFO;
        # kept at WARNING so they stay out of production logs.
        "hoteza": {
            "level": "WARNING",
        },
        **{name: {"level": "WARNING"} for name in _QUIET_LOGGERS},
    },
}
