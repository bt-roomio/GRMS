from admin_panel.swagger.tenants import AdminTenantListSwagger

from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.permission import IsSuperUser
from main.models import Tenant
from main.serializers.tenant import TenantSerializer


class AdminTenantListView(APIView):
    permission_classes = (IsSuperUser,)

    @swagger_auto_schema(
        tags=["Admin Panel"],
        responses=AdminTenantListSwagger,
        security=[{"Bearer": []}],
        operation_description="**Superuser only.** Returns a list of all tenants.",
    )
    def get(self, request):
        tenants = Tenant.objects.all().order_by("title")
        serializer = TenantSerializer(tenants, many=True)
        return Response(serializer.data)
