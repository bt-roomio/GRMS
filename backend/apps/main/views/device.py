from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.pagination import pagination
from main.models import Device
from main.serializers.device import DeviceSerializer, DeviceFilterParams


class DeviceListView(APIView):
    def get(self, request):
        params = DeviceFilterParams.check(request.GET)
        queryset = Device.objects.filter(tenant=request.user.tenant)
        serializer = DeviceSerializer(queryset, many=True)
        data = pagination(queryset, serializer, params.get("page"), params.get("size"))
        return Response(data)
