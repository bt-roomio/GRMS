from django.db.models import Q

from rest_framework.generics import get_object_or_404

from main.models import TenantGroup
from users.models import User
from users.utils.tenant_access import available_tenants_qs


def scoped_tenants(request):
    """
    Tenants the caller may administer.

    A plain superuser gets all of them; a superuser pinned to a chain
    (`tenant_group`) gets only that chain's hotels.
    """
    return available_tenants_qs(request.user)


def get_scoped_tenant_or_404(request, tenant_id):
    """404 rather than 403: a chain admin should not learn that other hotels exist."""
    return get_object_or_404(scoped_tenants(request), pk=tenant_id)


def scoped_groups(request):
    """The chains the caller may touch: their own, or all of them."""
    if request.user.tenant_group_id:
        return TenantGroup.objects.filter(pk=request.user.tenant_group_id)
    return TenantGroup.objects.all()


def scoped_users(request):
    """
    Accounts the caller may administer: the staff of the hotels in scope plus the
    admins of the chains in scope.

    Both halves are needed because a chain admin has no `tenant` of their own —
    filtering by hotel alone would leave those accounts unreachable.

    Unpinned superusers are then subtracted, and the exclusion is what makes the
    scope safe: such an account reaches the whole system, and it may well sit in
    a hotel (`tenant` set, no chain pin), so the first half would otherwise hand
    a chain admin the password of a system-wide account — an escalation out of
    their own chain. These accounts are managed out of band instead.
    """
    reachable = User.objects.filter(Q(tenant__in=scoped_tenants(request)) | Q(tenant_group__in=scoped_groups(request)))
    return reachable.exclude(is_superuser=True, tenant_group__isnull=True)


def get_scoped_user_or_404(request, user_id):
    """404 rather than 403: the caller should not learn that unreachable accounts exist."""
    return get_object_or_404(scoped_users(request), pk=user_id)


def scoped_group_id(request):
    """The chain a newly created tenant must land in, or None for a plain superuser."""
    return request.user.tenant_group_id
