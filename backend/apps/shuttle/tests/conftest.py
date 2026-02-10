"""
Shared pytest configuration for shuttle tests.

This conftest.py handles fixture loading for both consumer tests (pytest-style)
and REST tests (Django TestCase style) to avoid conflicts when running together.
"""
import pytest
from django.core.management import call_command


# Common fixtures used by both consumer and REST tests
COMMON_FIXTURES = [
    "tenant_profile.yaml",
    "tenant.yaml",
    "customer.yaml",
    "roles_permissions.yaml",
    "users.yaml",
    "room.yaml",
    "device_profile.yaml",
    "device.yaml",
    "attribute_kv.yaml",
]

# Additional fixtures for REST tests
REST_FIXTURES = [
    "ts_dictionary.yaml",
    "ts_kv_latest.yaml",
]

# Additional fixtures for consumer tests
CONSUMER_FIXTURES = [
    "group.yaml",
    "staff.yaml",
    "guest.yaml",
    "card.yaml",
    "card_log.yaml",
]


@pytest.fixture(scope="session", autouse=True)
def load_all_fixtures(django_db_setup, django_db_blocker):
    """
    Load all fixtures once for the entire test session.
    This prevents conflicts between consumer and REST tests.
    """
    with django_db_blocker.unblock():
        all_fixtures = COMMON_FIXTURES + REST_FIXTURES + CONSUMER_FIXTURES
        call_command("loaddata", *all_fixtures, verbosity=0)
