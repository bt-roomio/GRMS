from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission
from rest_framework.views import Http404


def check_for_tenant(func):
    def check(view, request, *args, **kwargs):
        if not request.user.tenant_id:
            raise Http404("Tenant not found!")
        return func(view, request, *args, **kwargs)

    return check


def check_perms(perms):
    def wrapper(func):
        def check(view, request, *args, **kwargs):
            access = False

            for group in request.user.groups.prefetch_related("permissions").all():
                for x in group.permissions.select_related("content_type"):
                    if x.codename in perms:
                        access = True

            if not access:
                raise PermissionDenied()

            return func(view, request, *args, **kwargs)

        return check

    return wrapper


class IsGroupUser(BasePermission):
    groups = []

    def has_permission(self, request, view):
        user = request.user
        return user.is_authenticated and user.groups.filter(name__in=self.groups).exists()


class IsSysAdmin(IsGroupUser):
    groups = ["SYS_ADMIN"]


class IsTenantAdmin(IsGroupUser):
    groups = ["TENANT_ADMIN"]


class IsTenantAndSysAdmin(IsGroupUser):
    groups = ["TENANT_ADMIN", "SYS_ADMIN"]
