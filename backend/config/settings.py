import os
import sys
from datetime import timedelta
from pathlib import Path

from celery.schedules import crontab
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "ABCD")

# TESTING mode
TESTING = "test" in sys.argv

DEBUG = os.getenv("DJANGO_DEBUG")

# 'DJANGO_ALLOWED_HOSTS' should be a single string of hosts with a space between each.
# For example: 'DJANGO_ALLOWED_HOSTS=localhost 127.0.0.1 [::1]'
ALLOWED_HOSTS = list(filter(None, [*os.getenv("DJANGO_ALLOWED_HOSTS", "").split(" ")]))

# Append module dir
sys.path.append(os.path.join(BASE_DIR, "apps"))

# Application definition

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Libraries
    "celery",
    "rest_framework",
    "django_filters",
    "django_celery_results",
    "django_celery_beat",
    "corsheaders",
    "drf_yasg",
    "channels",
    "channels_demultiplexer",
    "django_prometheus",
    # APPS
    "core",
    "users",
    "main",
    "shuttle",
    "access_manager",
    "services",
]

MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    # Should be start of middleware
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "core.utils.middleware.CheckForTenantMiddleware",
    # Should be end of middleware
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

ROOT_URLCONF = "config.urls"

# 'CORS_ORIGIN_WHITELIST' should be a single string of hosts with a space between each.
# For example: 'CORS_ORIGIN_WHITELIST=http://localhost:8000'
CORS_ORIGIN_WHITELIST = list(filter(None, [*os.getenv("DJANGO_CORS_ORIGIN_WHITELIST", "").split(" ")]))
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^http://localhost:\d+$",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "apps/core/templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "postgres"),
        "USER": os.getenv("POSTGRES_USER", "postgres"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
        "HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "PORT": os.getenv("POSTGRES_PORT", 5432),
        "CONN_MAX_AGE": 60,
    }
}

# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTH_USER_MODEL = "users.User"

AUTHENTICATION_BACKENDS = ["core.utils.backends.CustomBackend"]

# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = os.getenv("TIME_ZONE", "UTC")

USE_I18N = True

USE_TZ = bool(os.getenv("USE_TZ", 1))

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "static")
MEDIA_URL = "media/"
MEDIA_ROOT = os.path.join(BASE_DIR, MEDIA_URL)


# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"


# Email settings
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.mail.ru")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", True)
EMAIL_PORT = os.getenv("EMAIL_PORT", 2525)
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
SERVER_EMAIL = EMAIL_HOST_USER
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# Rest Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ("rest_framework_simplejwt.authentication.JWTAuthentication",),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "core.utils.pagination.PageSizePagination",
    "PAGE_SIZE": 15,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
}

SWAGGER_SETTINGS = {
    "PERSIST_AUTH": True,
    "USE_SESSION_AUTH": False,
    "SECURITY_DEFINITIONS": {"Bearer": {"type": "apiKey", "name": "Authorization", "in": "header"}},
}

FRONTEND_DOMAIN = os.getenv("FRONTEND_DOMAIN", "http://localhost:3000")
FRONTEND_ACTIVATION_URL = os.getenv("FRONTEND_ACTIVATION_URL", f"{FRONTEND_DOMAIN}/activate")
COMPANY_NAME = os.getenv("COMPANY_NAME", "Room.io")

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", 6379)

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [(REDIS_HOST, REDIS_PORT)],
        },
    },
}

RABBIT_HOST = os.getenv("RABBIT_HOST", "rabbitmq")
RABBIT_PORT = os.getenv("RABBIT_PORT", 5672)
RABBIT_LOGIN = os.getenv("RABBIT_LOGIN", "guest")
RABBIT_PASSWORD = os.getenv("RABBIT_PASSWORD", "guest")

WS_INTERVAL = os.getenv("WS_INTERVAL", 5)

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": os.getenv("CACHE_LOCATION", "cache_table"),
    }
}

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_TASK_IGNORE_RESULT = True
CELERY_RESULT_BACKEND = None
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True

CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
CELERY_BEAT_SCHEDULE = {
    "auto-checkout": {
        "task": "main.tasks.auto_check_out",
        "schedule": 30.0,
    },
    "clean_logs": {
        "task": "shuttle.tasks.delete_old_logs",
        "schedule": crontab(hour="0", minute="0"),
    },
}

HOTEZA_WHITELIST = list(filter(None, [*os.getenv("HOTEZA_WHITELIST", "").split(" ")]))

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
        "verbose_with_location": {
            "format": "[{levelname}] {asctime} {pathname}:{lineno} | {message}",
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
            "class": "rich.logging.RichHandler",
        },
        "file": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "fail_request.log",
            "formatter": "verbose",
            "maxBytes": 1024 * 1024 * 15,  # 1 MB
            "backupCount": 3,
        },
        "file_hoteza_app": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "fail_request_hoteza.log",
            "formatter": "verbose",
            "maxBytes": 1024 * 1024 * 15,  # 1 MB
            "backupCount": 3,
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "propagate": False,
            "level": "WARNING",
        },
        "hoteza": {
            "handlers": ["file_hoteza_app"],
            "level": "WARNING",
            "propagate": False,
        },
        "core": {
            "handlers": ["console"],
            "propagate": False,
            "level": "WARNING",
        },
    },
}
