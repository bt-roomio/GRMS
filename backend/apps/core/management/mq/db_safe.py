"""Thread-local DB connection guard shared across the MQ package.

Sync handlers run in a reused thread pool (via ``sync_to_async(...,
thread_sensitive=False)``). A connection closed by PgBouncer's
SERVER_IDLE_TIMEOUT lingers in the thread-local and raises ``InterfaceError``
on next use; ``close_old_connections()`` detects and drops it.
"""

from django.db import close_old_connections


def _db_safe(func):
    """Wrap ``func`` so stale thread-local DB connections are dropped before/after each call."""

    def wrapper(*args, **kwargs):
        close_old_connections()
        try:
            return func(*args, **kwargs)
        finally:
            close_old_connections()

    return wrapper
