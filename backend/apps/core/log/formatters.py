import logging
from datetime import UTC, datetime

import orjson

# Attributes every LogRecord has; anything else on a record came from `extra=`.
_RECORD_ATTRS = frozenset(vars(logging.LogRecord("", 0, "", 0, "", None, None))) | {
    "message",
    "asctime",
    "taskName",
    # Set by ContextFilter.
    "log_context",
    "ctx",
}


class JSONFormatter(logging.Formatter):
    """
    One JSON object per line, for log shippers (Loki, Vector, …).

    Keys: ts (UTC, ISO 8601), level, logger, message, location, process, then
    the log context (request_id, task_id, tenant_id, …), any ``extra=`` fields
    and ``exc_info`` / ``stack_info`` when present.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "location": f"{record.module}:{record.lineno}",
            "process": record.process,
            **getattr(record, "log_context", {}),
            **{key: value for key, value in vars(record).items() if key not in _RECORD_ATTRS},
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        elif record.exc_text:
            payload["exc_info"] = record.exc_text
        if record.stack_info:
            payload["stack_info"] = self.formatStack(record.stack_info)
        return orjson.dumps(payload, default=str, option=orjson.OPT_NON_STR_KEYS).decode()
