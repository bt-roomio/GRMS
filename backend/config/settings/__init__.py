"""
Django settings, assembled from topic components by django-split-settings.

Every component runs in this module's namespace, in the order listed below,
so a later component may override what an earlier one set.
https://github.com/wemake-services/django-split-settings
"""

from split_settings.tools import include

# Bootstrap first: loads .env and puts apps/ on sys.path before any component
# reads os.getenv or imports project code.
from config.settings.components import BASE_DIR  # noqa: F401

include(
    "components/base.py",
    "components/security.py",
    "components/auth.py",
    "components/database.py",
    "components/redis.py",
    "components/drf.py",
    "components/celery.py",
    "components/mail.py",
    "components/monitoring.py",
    "components/integrations.py",
    "components/fleet.py",
    "components/alarms.py",
    "components/brute_force_protection.py",
    "components/nodered.py",
    "components/logging.py",
)
