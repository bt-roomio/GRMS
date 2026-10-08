"""
Log context carried in a ContextVar, so it follows the current request/task
through sync code, asyncio tasks and asgiref's sync_to_async threads.

    with log_context(device_id=device.id):
        logger.info("Processing")   # -> ... [request_id=… device_id=…] Processing
"""

import re
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Any

# The default dict is shared, which is safe: bind() always sets a new dict and
# nothing mutates the stored one in place.
_context: ContextVar[dict[str, Any]] = ContextVar("log_context", default={})

# The HttpRequest being served. user/tenant are read from it lazily by
# ContextFilter, because DRF authenticates inside the view, after middleware.
current_request: ContextVar[Any] = ContextVar("log_request", default=None)

# Inbound X-Request-ID values are echoed into logs and response headers, so only
# short, plain ids are trusted; anything else is replaced with a fresh one.
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def get_context() -> dict[str, Any]:
    return _context.get()


def bind(**values: Any) -> Token:
    """Add values on top of the current context; undo with :func:`unbind`."""
    return _context.set({**_context.get(), **values})


def unbind(token: Token) -> None:
    _context.reset(token)


@contextmanager
def log_context(**values: Any) -> Iterator[None]:
    token = bind(**values)
    try:
        yield
    finally:
        unbind(token)


def new_request_id() -> str:
    return uuid.uuid4().hex


def clean_request_id(value: str | None) -> str:
    if value and _REQUEST_ID_RE.match(value):
        return value
    return new_request_id()
