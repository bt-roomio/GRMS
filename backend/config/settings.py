import os
import re
import sys
import warnings
from datetime import timedelta
from pathlib import Path

from celery.schedules import crontab
from dotenv import load_dotenv

# Suppress django-prometheus database initialization warnings
warnings.filterwarnings(
    "ignore",
    message="Accessing the database during app initialization is discouraged",
    category=RuntimeWarning,
    module="django.db.backends.utils",
)

# Load environment variables from .env file
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "ABCD")

# TESTING mode - check both sys.argv and environment variable
TESTING = "test" in sys.argv or os.getenv("DJANGO_TESTING", "").lower() in ("1", "true", "yes")

# For pytest
TEST_RUNNER = "config.pytest_runner.PytestTestRunner"

DEBUG = os.getenv("DJANGO_DEBUG")

# 'DJANGO_ALLOWED_HOSTS' should be a single string of hosts with a space between each.
# For example: 'DJANGO_ALLOWED_HOSTS=localhost 127.0.0.1 [::1]'
ALLOWED_HOSTS = list(filter(None, [*os.getenv("DJANGO_ALLOWED_HOSTS", "").split(" ")]))

# Silence system checks
# auth.W004: Email is unique per is_active=True via UniqueConstraint
SILENCED_SYSTEM_CHECKS = [
    "auth.W004",
]

# Append module dir
sys.path.append(os.path.join(BASE_DIR, "apps"))

# Application definition

INSTALLED_APPS = [
    "daphne",
    "django_prometheus",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    # Libraries
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.microsoft",
    "celery",
    "rest_framework",
    "django_filters",
    "django_celery_results",
    "django_celery_beat",
    "corsheaders",
    "drf_yasg",
    "channels",
    "channels_demultiplexer",
    # APPS
    "core",
    "users",
    "main",
    "shuttle",
    "access_manager",
    "services",
    "mews",
]

MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    # Should be start of middleware
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.utils.middleware.CheckForTenantMiddleware",
    # allauth
    "allauth.account.middleware.AccountMiddleware",
    "main.middlewares.device.DeviceMetricsMiddleware",
    # Should be end of middleware
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

PROMETHEUS_MULTIPROC_DIR = os.environ.get("PROMETHEUS_MULTIPROC_DIR", "/tmp/prometheus_multiproc")
os.makedirs(PROMETHEUS_MULTIPROC_DIR, exist_ok=True)
os.environ["PROMETHEUS_MULTIPROC_DIR"] = PROMETHEUS_MULTIPROC_DIR

# Gateway monitoring settings
DJANGO_IS_MONITORING_GATEWAYS = os.getenv("DJANGO_IS_MONITORING_GATEWAYS", "True").lower() in ("true", "1", "yes")
DJANGO_MONITORING_EXCLUDED_GATEWAYS = list(
    filter(None, re.split(r"[,\s]+", os.getenv("DJANGO_MONITORING_EXCLUDED_GATEWAYS", "")))
)

ROOT_URLCONF = "config.urls"

# 'CORS_ORIGIN_WHITELIST' should be a single string of hosts with a space between each.
# For example: 'CORS_ORIGIN_WHITELIST=http://localhost:8000'
CORS_ORIGIN_WHITELIST = list(filter(None, [*os.getenv("DJANGO_CORS_ORIGIN_WHITELIST", "").split(" ")]))
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^http://localhost:\d+$",
]
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = list(filter(None, [*os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(" ")]))

USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SAMESITE = "None"
CSRF_COOKIE_SAMESITE = "None"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True


FRONTEND_DOMAIN = os.getenv("FRONTEND_DOMAIN", "http://localhost:5173")
FRONTEND_ACTIVATION_URL = os.getenv("FRONTEND_ACTIVATION_URL", f"{FRONTEND_DOMAIN}/activate")

# allauth account configuration for email-only user model (no username field)
SITE_ID = 1
ACCOUNT_ADAPTER = "users.auth.adapters.NoSignupAccountAdapter"
SOCIALACCOUNT_ADAPTER = "users.auth.adapters.NoNewSocialSignupAdapter"
SOCIALACCOUNT_AUTO_SIGNUP = False
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_STORE_TOKENS = True
SOCIALACCOUNT_QUERY_EMAIL = True
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_USER_MODEL_USERNAME_FIELD = None

LOGIN_REDIRECT_URL = FRONTEND_DOMAIN
LOGOUT_REDIRECT_URL = "/admin"

KC_BASE_URL = os.getenv("KEYCLOAK_BASE_URL", "http://localhost:8080")
KC_REALM = os.getenv("KEYCLOAK_REALM", "realm_name")
KC_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "client_id")
KC_CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_SECRET", "")

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APPS": [
            {
                "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
                "secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
                "key": "",
                "sites": [SITE_ID],
            }
        ],
        "SCOPE": ["openid", "email", "profile"],
        "AUTH_PARAMS": {"prompt": "select_account"},
        "FETCH_USERINFO": True,
    },
    "microsoft": {
        "SCOPE": ["openid", "email", "profile", "offline_access", "User.Read"],
        "AUTH_PARAMS": {"prompt": "select_account"},
        "FETCH_USERINFO": True,
        "APPS": [
            {
                "provider_id": "microsoft",
                "name": "Microsoft",
                "client_id": os.getenv("MS_CLIENT_ID", ""),
                "secret": os.getenv("MS_CLIENT_SECRET", ""),
                "sites": [SITE_ID],
            }
        ],
    },
    "openid_connect": {
        "OAUTH_PKCE_ENABLED": True,
        "APPS": [
            {
                "provider_id": "keycloak",
                "name": "Login via SSO",
                "client_id": KC_CLIENT_ID,
                "secret": KC_CLIENT_SECRET,
                "settings": {
                    "server_url": f"{KC_BASE_URL}/realms/{KC_REALM}/.well-known/openid-configuration",
                    "issuer": f"{KC_BASE_URL}/realms/{KC_REALM}",
                    "claims_standard": ["email", "preferred_username"],
                    "scopes": ["openid", "email", "profile"],
                },
            },
        ],
    },
}

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


IS_CELERY = os.getenv("IS_CELERY", 0)

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django_prometheus.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "postgres"),
        "USER": os.getenv("POSTGRES_USER", "postgres"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
        "HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "PORT": os.getenv("POSTGRES_PORT", 5432),
        "CONN_MAX_AGE": 0 if (IS_CELERY or TESTING) else 60,
        "OPTIONS": {"application_name": os.getenv("PGAPPNAME", "grms-web")},
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

AUTHENTICATION_BACKENDS = [
    "core.utils.backends.CustomBackend",
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

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

COMPANY_NAME = os.getenv("COMPANY_NAME", "Room.io")

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", 6379)

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [(REDIS_HOST, REDIS_PORT)],
            "serializer_format": "uuidjson",  #  Registered in core.apps
        },
    },
}

RABBIT_HOST = os.getenv("RABBIT_HOST", "rabbitmq")
RABBIT_PORT = os.getenv("RABBIT_PORT", 5672)
RABBIT_LOGIN = os.getenv("RABBIT_LOGIN", "guest")
RABBIT_PASSWORD = os.getenv("RABBIT_PASSWORD", "guest")

WEBRTC_BROKER_URL = os.getenv("WEBRTC_BROKER_URL", "https://webrtc.leto.tais.su")

WS_INTERVAL = os.getenv("WS_INTERVAL", 5)

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": os.getenv("CACHE_LOCATION", "cache_table"),
    }
}

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_TASK_IGNORE_RESULT = True
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1")
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True

CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
CELERY_BEAT_SCHEDULE = {
    "auto-checkout": {
        "task": "main.tasks.auto_check_out",
        "schedule": 30.0,
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
        "schedule": 60.0,  # Every minute
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
            "format": "{levelname} {asctime} {message}",
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
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "simple",
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
            "level": "WARNING",
        },
        "main": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "mews": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "services": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "shuttle": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "hoteza": {
            "handlers": ["file_hoteza_app"],
            "level": "WARNING",
            "propagate": False,
        },
        "core": {
            "handlers": ["console"],
            "propagate": False,
            "level": "DEBUG",
        },
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}
