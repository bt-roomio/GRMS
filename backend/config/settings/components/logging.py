import os

from config.settings.components import env_bool

_LOG_LEVEL = os.getenv("DJANGO_LOG_LEVEL", "WARNING").upper()
_LOG_FORMATTER = os.getenv("DJANGO_LOG_FORMATTER", "simple")
_LOG_SQL = env_bool("DJANGO_LOG_SQL", "false")

# Project apps log at _LOG_LEVEL into the console, without propagating to root.
_APP_LOGGERS = ("celery", "main", "mews", "services", "shuttle", "access_manager", "hoteza", "core")

# All logs go to stdout/stderr — rotation and retention are handled by Docker
# (x-logging in deploy/docker-compose.yml: json-file, max-size 50m, max-file 5).
# File handlers are deliberately unused: RotatingFileHandler is not
# multiprocess-safe with GUNICORN_WORKERS > 1, and writing inside the container
# without a volume is lost on redeploy.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    # {name} is present in every format: all subsystems log into a single stdout,
    # and the logger name is the only way to tell security/hoteza/… apart when
    # reading them (`docker logs django | grep ' security '`).
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {name} {module}:{lineno} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {asctime} {name} {message}",
            "style": "{",
        },
        "verbose_with_location": {
            "format": "[{levelname}] {asctime} [{name}] {pathname}:{lineno} | {message}",
            "style": "{",
        },
    },
    "filters": {
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": _LOG_FORMATTER,
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": _LOG_LEVEL,
        },
        # INFO is set explicitly instead of _LOG_LEVEL: lockout and successful
        # login events are always needed, regardless of overall log verbosity.
        "security": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        **{name: {"handlers": ["console"], "level": _LOG_LEVEL, "propagate": False} for name in _APP_LOGGERS},
        "pika": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        **(
            {
                "django.db.backends": {
                    "handlers": ["console"],
                    "level": "DEBUG",
                    "propagate": False,
                }
            }
            if _LOG_SQL
            else {}
        ),
    },
}
