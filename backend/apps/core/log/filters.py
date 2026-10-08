import logging
from typing import Any

from django.utils.functional import SimpleLazyObject, empty

from core.log.context import current_request, get_context


def _request_user_fields(request: Any) -> dict[str, Any]:
    """
    user_id/tenant_id of the request, but only if authentication already ran.

    Logging must never trigger a DB query, so a SimpleLazyObject user that has
    not been evaluated yet (AuthenticationMiddleware) is skipped; once DRF
    authenticates it replaces request.user with the real object.
    """
    user = vars(request).get("user")
    if isinstance(user, SimpleLazyObject):
        user = user._wrapped
        if user is empty:
            return {}
    if user is None or not getattr(user, "is_authenticated", False):
        return {}
    fields = {"user_id": user.pk}
    tenant_id = vars(user).get("tenant_id")
    if tenant_id is not None:
        fields["tenant_id"] = tenant_id
    return fields


class ContextFilter(logging.Filter):
    """
    Stamps the current log context onto every record:

    - ``record.log_context`` — dict, used by JSONFormatter;
    - ``record.ctx`` — ``"[key=value …] "`` or ``""``, used by the text formats.

    Attach it to handlers (not loggers): handler filters also see records that
    propagated up from child loggers.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        context = dict(get_context())
        request = current_request.get()
        if request is not None:
            context.update(_request_user_fields(request))
        record.log_context = context
        record.ctx = "[" + " ".join(f"{key}={value}" for key, value in context.items()) + "] " if context else ""
        return True
