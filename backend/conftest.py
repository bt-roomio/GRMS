import os
import sys

# CRITICAL: Set environment variable BEFORE Django imports to ensure TESTING=True in settings.py
# This must run before any Django configuration happens
os.environ["DJANGO_TESTING"] = "1"

# Also add "test" to sys.argv for compatibility
if "test" not in sys.argv and "pytest" in sys.argv[0]:
    sys.argv.insert(1, "test")


def pytest_configure(config):
    """
    Fix for psycopg2.errors.InvalidCursorName: cursor does not exist

    PostgreSQL cursors exist only within a transaction, but Django's test framework
    creates a new transaction for each test. When CONN_MAX_AGE > 0 (persistent connections),
    the connection is reused but the transaction ends, making old cursors invalid.

    Solution: Disable persistent connections during tests by setting CONN_MAX_AGE = 0

    This hook runs before Django is initialized, ensuring the setting is applied early.
    """
    from django.conf import settings

    # Disable persistent connections for all databases during testing
    for db_settings in settings.DATABASES.values():
        db_settings["CONN_MAX_AGE"] = 0
