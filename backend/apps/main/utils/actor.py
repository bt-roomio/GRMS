from main.models import Guest


def actor_from_context(context: dict) -> tuple[str, object | None]:
    """Return (source, user) of a change from serializer context.

    "source" is a Guest.SOURCE (defaults to ROOMIO); "user" is the acting user, kept only when
    authenticated and omitted for integrations.
    """
    user = context.get("user")
    if not getattr(user, "is_authenticated", False):
        user = None
    return context.get("source", Guest.SOURCE.ROOMIO), user


def actor_id(user) -> str | None:
    return str(user.id) if user else None
