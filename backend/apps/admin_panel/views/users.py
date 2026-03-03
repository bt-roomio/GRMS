from admin_panel.swagger.users import AdminTenantUsersSwagger

from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.permission import IsSuperUser
from main.models import Tenant
from users.models import User
from users.serializers.user import UserSerializer


class AdminTenantUsersView(APIView):
    permission_classes = (IsSuperUser,)

    @swagger_auto_schema(
        tags=["Admin Panel"],
        responses=AdminTenantUsersSwagger,
        security=[{"Bearer": []}],
        operation_description="**Superuser only.** Returns a list of active users for the given tenant.",
    )
    def get(self, request, tenant_id):
        get_object_or_404(Tenant, id=tenant_id)
        queryset = User.objects.prefetch_related("roles").filter(tenant_id=tenant_id, is_active=True)
        serializer = UserSerializer(queryset, many=True)
        return Response(serializer.data)
