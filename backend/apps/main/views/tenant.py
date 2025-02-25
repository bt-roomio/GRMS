from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.permission import IsSuperUser
from main.models import Tenant
from main.serializers.tenant import TenantSerializer
from main.swagger.tenant import TenantSwagger


class TenantListView(APIView):
    permission_classes = (IsSuperUser,)

    @swagger_auto_schema(tags=["Main, Tenant"], responses=TenantSwagger)
    def get(self, request):
        tenants = Tenant.objects.all()
        serializer = TenantSerializer(tenants, many=True)
        return Response(serializer.data)
