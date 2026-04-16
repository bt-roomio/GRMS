from admin_panel.swagger.roles import AdminTenantRolesSwagger

from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.permission import IsSuperUser
from main.models import Tenant
from users.models import Role
from users.serializers.role import RoleSimpleSerializer


class AdminTenantRolesView(APIView):
    permission_classes = (IsSuperUser,)

    @swagger_auto_schema(
        tags=["Admin Panel"],
        responses=AdminTenantRolesSwagger,
        security=[{"Bearer": []}],
        operation_description="**Superuser only.** Returns a list of roles for the given tenant.",
    )
    def get(self, request, tenant_id):
        get_object_or_404(Tenant, id=tenant_id)
        queryset = Role.objects.filter(tenant_id=tenant_id)
        serializer = RoleSimpleSerializer(queryset, many=True)
        return Response(serializer.data)
