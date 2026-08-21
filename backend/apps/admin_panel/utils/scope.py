from rest_framework.generics import get_object_or_404

from users.utils.tenant_access import available_tenants_qs


def scoped_tenants(request):
    """
    Tenants the caller may administer.

    A plain superuser gets all of them; a superuser pinned to a chain
    (`tenant_group`) gets only that chain's hotels.
    """
    return available_tenants_qs(request.user)


def get_scoped_tenant(request, tenant_id):
    """404 rather than 403: a chain admin should not learn that other hotels exist."""
    return get_object_or_404(scoped_tenants(request), pk=tenant_id)


def scoped_group_id(request):
    """The chain a newly created tenant must land in, or None for a plain superuser."""
    return request.user.tenant_group_id
