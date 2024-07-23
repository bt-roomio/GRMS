from rest_framework.permissions import BasePermission
from rest_framework.views import Http404


def check_for_tenant(func):
    def check(view, request, *args, **kwargs):
        if not request.user.tenant_id:
            raise Http404("Tenant not found!")
        return func(view, request, *args, **kwargs)

    return check


def permission(perms):
    def wrapper(func):
        def check(view, request, *args, **kwargs):
            for group in request.user.groups.all():
                for perm in group.permissions.select_related("content_type"):
                    print(perm)
            # if not request.user.has_perm(perm):
            #     raise PermissionDenied()

            return func(view, request, *args, **kwargs)

        return check

    return wrapper


class IsGroupUser(BasePermission):
    groups = []

    def has_permission(self, request, view):
        user = request.user
        return user.is_authenticated and user.groups.filter(name__in=self.groups).exists()


class IsSysAdmin(IsGroupUser):
    groups = "SYS_ADMIN"


class IsTenantAdmin(IsGroupUser):
    groups = "TENANT_ADMIN"


class IsTenantAndSysAdmin(IsGroupUser):
    groups = ["TENANT_ADMIN", "SYS_ADMIN"]
