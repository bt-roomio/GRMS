from admin_panel.swagger.impersonate import ImpersonateSwagger
from admin_panel.utils.scope import scoped_tenants

from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.permission import IsSuperUser
from users.models import User
from users.serializers.jwt_token import build_tokens_for
from users.utils.tenant_access import is_unscoped_superuser


class ImpersonateView(APIView):
    permission_classes = (IsSuperUser,)

    @swagger_auto_schema(
        tags=["Admin Panel"],
        responses=ImpersonateSwagger,
        security=[{"Bearer": []}],
        operation_description="**Superuser only.** Generates JWT tokens on behalf of the specified user.",
    )
    def post(self, request, user_id):
        # A chain admin may only step into users of their own chain. An unpinned
        # superuser reaches everyone, hotel-less accounts (other superusers, chain
        # admins) included — filtering by tenant alone would silently drop those.
        reachable = User.objects.all()
        if not is_unscoped_superuser(request.user):
            reachable = reachable.filter(tenant__in=scoped_tenants(request))
        user = get_object_or_404(reachable, id=user_id, is_active=True)
        return Response(build_tokens_for(user))
