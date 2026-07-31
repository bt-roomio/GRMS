def tenant_scope_for_user(user):
    """
    Which tenant's nodes this user may see.

    Superusers operate across the whole fleet, so they get ``None``, which the
    querysets read as "do not filter".
    """
    if getattr(user, "is_superuser", False):
        return None
    return getattr(user, "tenant_id", None)


def tenant_scope(request):
    return tenant_scope_for_user(request.user)
