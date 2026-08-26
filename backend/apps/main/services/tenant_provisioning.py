from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Permission
from django.db import transaction

from core.utils.constants import UI_PERMISSIONS
from main.models import DeviceProfile, Tenant, TenantGroup, TenantProfile
from users.models import Role, User

DEFAULT_DEVICE_PROFILES = ("Default", "Integration Devices", "Card Reader")


@transaction.atomic
def provision_tenant(*, title, email, password, group=None):
    """
    Create a hotel together with its admin role, admin user and default profiles.

    Shared by the admin API and the `create_tenant` command so the two cannot drift.
    """
    tenant_profile, _ = TenantProfile.objects.get_or_create(name="Default", defaults={"is_default": True})
    tenant = Tenant.objects.create(tenant_profile=tenant_profile, title=title, group=group)
    Tenant.objects.get_or_create(tenant_profile=tenant_profile, title="Default")

    role, _ = Role.objects.get_or_create(name="TENANT_ADMIN", tenant=tenant)
    role.permissions.add(*Permission.objects.all())
    role.additional_info = {"ui_permissions": UI_PERMISSIONS}
    role.save()

    user = User.objects.create(tenant=tenant, email=email, password=make_password(password))
    user.roles.add(role)

    for name in DEFAULT_DEVICE_PROFILES:
        DeviceProfile.objects.get_or_create(name=name, tenant=tenant, type="DEFAULT")

    return tenant


@transaction.atomic
def provision_tenant_group(*, email, password, **group_fields):
    """
    Create a hotel chain together with its administrator.

    The chain admin is a superuser carrying `tenant_group`: the pin narrows the
    system-wide reach of `is_superuser` down to this chain's hotels, so no role
    is needed (see `users.utils.tenant_access.available_tenants_qs`). The user
    has no `tenant` of their own — they administer hotels rather than live in one.
    """
    group = TenantGroup.objects.create(**group_fields)
    User.objects.create(
        email=email,
        password=make_password(password),
        tenant_group=group,
        is_superuser=True,
    )
    return group


@transaction.atomic
def dissolve_tenant_group(group):
    """
    Delete a chain without promoting anybody.

    `User.tenant_group` is SET_NULL, so a chain admin would outlive the chain as an
    *unpinned* superuser — that is, with system-wide reach over every hotel. Their
    accounts are deactivated first; an unpinned superuser can reinstate them
    deliberately. The chain's hotels are untouched and simply become standalone.
    """
    group.users.update(is_active=False, tenant_group=None)
    group.delete()
