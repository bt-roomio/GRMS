"""Unit tests for the _db_safe connection guard."""

from unittest.mock import patch

import pytest

from core.management.mq import db_safe


def test_closes_before_and_after_and_returns_value():
    calls = []
    with patch.object(db_safe, "close_old_connections", lambda: calls.append("close")):
        wrapped = db_safe._db_safe(lambda x: x * 2)
        assert wrapped(5) == 10
    assert calls == ["close", "close"]


def test_closes_even_when_wrapped_raises():
    calls = []

    def boom():
        raise ValueError("x")

    with patch.object(db_safe, "close_old_connections", lambda: calls.append("close")):
        wrapped = db_safe._db_safe(boom)
        with pytest.raises(ValueError):
            wrapped()
    # closed before the call and again in the finally block
    assert calls == ["close", "close"]
