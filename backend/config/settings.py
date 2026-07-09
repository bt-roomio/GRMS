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
_test_arg_check = any(arg in sys.argv for arg in ["test"]) or any("pytest" in arg for arg in sys.argv)
_env_check = os.getenv("DJANGO_TESTING", "").lower() in ("1", "true", "yes")

TESTING = _test_arg_check or _env_check

# For pytest
TEST_RUNNER = "config.pytest_runner.PytestTestRunner"

DEBUG = os.getenv("DJANGO_DEBUG", "").lower() in ("1", "true", "yes")

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
    "rest_framework_simplejwt.token_blacklist",
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
    "admin_panel",
    "hoteza",
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
    "core.middleware.brute_force_protection.APIBruteForceProtectionMiddleware",
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
        "CONN_MAX_AGE": 0,
        "CONN_HEALTH_CHECKS": True,
        "DISABLE_SERVER_SIDE_CURSORS": True,
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


EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp-mail.outlook.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True") == "True"
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER)
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
FRONTEND_HOST = os.getenv("FRONTEND_HOST", "http://localhost")
FRONTEND_PORT = os.getenv("FRONTEND_PORT")


# Rest Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ("rest_framework_simplejwt.authentication.JWTAuthentication",),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "core.utils.pagination.PageSizePagination",
    "PAGE_SIZE": 15,
    "DEFAULT_THROTTLE_RATES": {
        "auth_token": "20/min",
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
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
            "serializer_format": "uuidjson",
            "capacity": 5000,
            "expiry": 30,
            "group_expiry": 86400,
            "channel_capacity": {
                "http.request": 200,
                "websocket.send*": 100,
            },
        },
    },
}

RABBIT_HOST = os.getenv("RABBIT_HOST", "rabbitmq")
RABBIT_PORT = os.getenv("RABBIT_PORT", 5672)
RABBIT_LOGIN = os.getenv("RABBIT_LOGIN", "guest")
RABBIT_PASSWORD = os.getenv("RABBIT_PASSWORD", "guest")

WEBRTC_BROKER_URL = os.getenv("WEBRTC_BROKER_URL")

WS_INTERVAL = os.getenv("WS_INTERVAL", 5)

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:{REDIS_PORT}/4",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {
                "max_connections": 100,
                "retry_on_timeout": True,
            },
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
            "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
        },
        "KEY_PREFIX": "grms",
        "TIMEOUT": 300,
    },
    "security": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:{REDIS_PORT}/2",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {
                "max_connections": 50,
                "retry_on_timeout": True,
            },
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
        },
        "KEY_PREFIX": "grms_security",
        "TIMEOUT": 900,
    },
    "http": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:{REDIS_PORT}/3",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {
                "max_connections": 50,
                "retry_on_timeout": True,
            },
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
        },
        "KEY_PREFIX": "grms_http",
        "TIMEOUT": 900,
    },
}

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_TASK_IGNORE_RESULT = True
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1")
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True


CELERY_BEAT_SCHEDULE = {
    "auto-checkout": {
        "task": "main.tasks.auto_check_out",
        "schedule": crontab(minute="*/5"),
    },
    "auto-block–guest": {
        "task": "main.tasks.auto_block",
        "schedule": 60.0,
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
        "schedule": crontab(hour=3, minute=0),  # каждую ночь в 3:00
    },
}

HOTEZA_WHITELIST = list(filter(None, [*os.getenv("HOTEZA_WHITELIST", "").split(" ")]))

CLIENT_TOKENS = os.getenv("CLIENT_TOKENS", "").split(" ")

_LOG_LEVEL = os.getenv("DJANGO_LOG_LEVEL", "WARNING").upper()
_LOG_FORMATTER = os.getenv("DJANGO_LOG_FORMATTER", "simple")
_LOG_SQL = os.getenv("DJANGO_LOG_SQL", "false").lower() in ("1", "true", "yes")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module}:{lineno} {process:d} {thread:d} {message}",
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
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": _LOG_FORMATTER,
        },
        "file": {
            "level": "WARNING",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "fail_request.log",
            "formatter": "verbose",
            "maxBytes": 1024 * 1024 * 15,  # 1 MB
            "backupCount": 3,
        },
        "file_hoteza_app": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "hoteza.log",
            "formatter": "verbose",
            "maxBytes": 1024 * 1024 * 15,  # 1 MB
            "backupCount": 3,
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": _LOG_LEVEL,
        },
        "celery": {
            "handlers": ["console"],
            "level": _LOG_LEVEL,
            "propagate": False,
        },
        "main": {
            "handlers": ["console"],
            "level": _LOG_LEVEL,
            "propagate": False,
        },
        "mews": {
            "handlers": ["console"],
            "level": _LOG_LEVEL,
            "propagate": False,
        },
        "services": {
            "handlers": ["console"],
            "level": _LOG_LEVEL,
            "propagate": False,
        },
        "shuttle": {
            "handlers": ["console"],
            "level": _LOG_LEVEL,
            "propagate": False,
        },
        "access_manager": {
            "handlers": ["console"],
            "level": _LOG_LEVEL,
            "propagate": False,
        },
        "hoteza": {
            "handlers": ["file_hoteza_app"],
            "level": _LOG_LEVEL,
            "propagate": False,
        },
        "core": {
            "handlers": ["console"],
            "level": _LOG_LEVEL,
            "propagate": False,
        },
        "security": {
            "handlers": ["console"],
            "level": _LOG_LEVEL,
            "propagate": False,
        },
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

from .components.brute_force_protection import BRUTE_FORCE_CONFIG  # noqa: E402 F401  # ty: ignore
