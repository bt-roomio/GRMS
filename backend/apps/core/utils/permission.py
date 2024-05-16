from rest_framework.exceptions import PermissionDenied
from rest_framework.views import Http404


def check_for_tenant(func):
    def check(view, request, *args, **kwargs):
        if not request.user.tenant_id:
            raise Http404('Tenant not found!')
        return func(view, request, *args, **kwargs)
    return check
