from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.permission import IsSuperUser
from main.models import Tenant
from main.serializers.tenant import TenantSerializer


class AdminTenantListView(APIView):
    permission_classes = (IsSuperUser,)

    def get(self, request):
        tenants = Tenant.objects.all().order_by("title")
        serializer = TenantSerializer(tenants, many=True)
        return Response(serializer.data)
