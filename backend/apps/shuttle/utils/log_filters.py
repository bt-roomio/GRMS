import logging
import re
from collections.abc import Mapping

_TOKEN_RE = re.compile(r"(token=)[^&\s\"']+")


class RedactTokenFilter(logging.Filter):
    """Masks ``token=...`` in the query string.

    The WebSocket JWT is passed in the URL (``/api/ws/v2/?token=...``), and uvicorn writes
    the full path into the handshake line, so a live access token ended up in the logs.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        if isinstance(args, tuple):
            record.args = tuple(_redact(a) for a in args)
        elif isinstance(args, Mapping):
            # logger.info("%(path)s", {...}): LogRecord keeps the dict as is.
            record.args = {k: _redact(v) for k, v in args.items()}
        return True


def _redact(value):
    return _TOKEN_RE.sub(r"\1***", value) if isinstance(value, str) else value
