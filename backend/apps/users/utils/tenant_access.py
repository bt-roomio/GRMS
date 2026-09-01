from django.apps import apps


def is_chain_admin(user):
    """A superuser pinned to one hotel chain — powerful, but only inside that chain."""
    return bool(user.is_superuser and user.tenant_group_id)


def is_unscoped_superuser(user):
    """A superuser with no chain pin: the only tier that reaches the whole system."""
    return bool(user.is_superuser and not user.tenant_group_id)


def available_tenants_qs(user):
    """
    Tenants the user is allowed to work with.

    Three tiers: a chain admin sees every hotel of their chain, an unpinned
    superuser sees everything, and everyone else sees exactly their own hotel.
    Ordinary users still get a one-item queryset, so callers never have to branch
    on user type.

    The pin only narrows `is_superuser`; on its own it grants nothing, which is
    why `is_chain_admin` demands both flags.
    """
    tenant_model = apps.get_model("main", "Tenant")

    if is_chain_admin(user):
        return tenant_model.objects.filter(group_id=user.tenant_group_id)

    if user.is_superuser:
        return tenant_model.objects.all()

    if user.tenant_id:
        return tenant_model.objects.filter(pk=user.tenant_id)

    return tenant_model.objects.none()


def scoped_tenant_ids(user):
    """The same scope as a set of strings, for comparing against untrusted input."""
    return {str(pk) for pk in available_tenants_qs(user).values_list("pk", flat=True)}
