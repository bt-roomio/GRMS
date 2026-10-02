import os
import sys
import warnings

from config.settings.components import BASE_DIR, env_bool, env_list

# Suppress django-prometheus database initialization warnings
warnings.filterwarnings(
    "ignore",
    message="Accessing the database during app initialization is discouraged",
    category=RuntimeWarning,
    module="django.db.backends.utils",
)

# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "ABCD")

# TESTING mode - check both sys.argv and environment variable
_test_arg_check = any(arg in sys.argv for arg in ["test"]) or any("pytest" in arg for arg in sys.argv)

TESTING = _test_arg_check or env_bool("DJANGO_TESTING")

# For pytest
TEST_RUNNER = "config.pytest_runner.PytestTestRunner"

DEBUG = env_bool("DJANGO_DEBUG")

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS")

# Silence system checks
# auth.W004: Email is unique per is_active=True via UniqueConstraint
SILENCED_SYSTEM_CHECKS = [
    "auth.W004",
]

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
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "drf_yasg",
    "channels",
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
    "fleet",
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
    # Should be end of middleware
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

ROOT_URLCONF = "config.urls"

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

COMPANY_NAME = os.getenv("COMPANY_NAME", "Room.io")
