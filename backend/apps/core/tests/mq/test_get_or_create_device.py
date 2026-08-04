"""Unit tests for get_or_create_device (create + concurrent-create IntegrityError fallback)."""

from contextlib import nullcontext
from unittest.mock import MagicMock, patch

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from core.management.mq.devices import get_device as gd

_FROM = {"id": "gw", "tenant_id": "t1", "device_profile_id": "p1"}


def _patch():
    """Shared patch set: Device, transaction.atomic (real nullcontext), Credentials, Relation, token."""
    return (
        patch.object(gd, "Device"),
        patch.object(gd.transaction, "atomic", side_effect=lambda *a, **k: nullcontext()),
        patch.object(gd, "DeviceCredentials"),
        patch.object(gd, "Relation"),
        patch.object(gd, "get_random_letter", return_value="tok"),
    )


def test_creates_when_absent():
    obj = MagicMock(id="new")
    Device, atomic, Creds, Rel, _tok = _patch()
    with Device as Device, atomic, Creds as Creds, Rel as Rel, _tok:
        Device.return_value = obj
        Device.objects.filter.return_value.first.return_value = None
        result = gd.get_or_create_device("sub", _FROM)

    assert result is obj
    obj.save.assert_called_once()
    Creds.objects.create.assert_called_once()
    Rel.objects.update_or_create.assert_called_once()


def test_returns_existing_on_integrity_error():
    """Parallel replica created the same (name, tenant) → we re-fetch instead of crashing the batch."""
    existing = MagicMock(id="e1")
    obj = MagicMock()
    obj.save.side_effect = IntegrityError("duplicate key")
    Device, atomic, Creds, Rel, _tok = _patch()
    with Device as Device, atomic, Creds, Rel as Rel, _tok:
        Device.return_value = obj
        Device.objects.filter.return_value.first.side_effect = [None, existing]
        result = gd.get_or_create_device("sub", _FROM)

    assert result is existing
    Rel.objects.update_or_create.assert_not_called()  # create path aborted before relation write


def test_returns_existing_on_validation_error():
    existing = MagicMock(id="e2")
    obj = MagicMock()
    obj.full_clean.side_effect = ValidationError("dup")
    Device, atomic, Creds, Rel, _tok = _patch()
    with Device as Device, atomic, Creds, Rel, _tok:
        Device.return_value = obj
        Device.objects.filter.return_value.first.side_effect = [None, existing]
        result = gd.get_or_create_device("sub", _FROM)

    assert result is existing
    obj.save.assert_not_called()  # full_clean failed first


def test_reraises_when_no_existing_after_conflict():
    obj = MagicMock()
    obj.save.side_effect = IntegrityError("duplicate key")
    Device, atomic, Creds, Rel, _tok = _patch()
    with Device as Device, atomic, Creds, Rel, _tok:
        Device.return_value = obj
        Device.objects.filter.return_value.first.side_effect = [None, None]
        with pytest.raises(IntegrityError):
            gd.get_or_create_device("sub", _FROM)
