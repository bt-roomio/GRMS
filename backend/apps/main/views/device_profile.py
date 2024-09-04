from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.pagination import pagination
from main.models import DeviceProfile
from main.serializers.device_profile import DeviceProfileSerializer, DeviceProfileFilterParams
from main.swagger.device_profile import DeviceProfileSwagger, DeviceProfileDetailSwagger


class DeviceProfileListView(APIView):
    @swagger_auto_schema(responses=DeviceProfileSwagger, query_serializer=DeviceProfileFilterParams())
    def get(self, request):
        params = DeviceProfileFilterParams.check(request.GET)
        queryset = DeviceProfile.objects.list(
            tenant=request.user.tenant,
            state=params.get("state"),
            search_field=params.get("search_field"),
            search_value=params.get("search_value"),
        )
        serializer = DeviceProfileSerializer(queryset, many=True)
        data = pagination(queryset, serializer, params.get("page"), params.get("size"))
        return Response(data)

    @swagger_auto_schema(responses=DeviceProfileSwagger, request_body=DeviceProfileSerializer)
    def post(self, request):
        serializer = DeviceProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(tenant_id=request.user.tenant_id)
        return Response(serializer.data, 201)


class DeviceProfileDetailView(APIView):
    @swagger_auto_schema(responses=DeviceProfileDetailSwagger)
    def get(self, request, pk):
        instance = get_object_or_404(DeviceProfile, pk=pk, tenant_id=request.user.tenant_id)
        serializer = DeviceProfileSerializer(instance)
        return Response(serializer.data)

    @swagger_auto_schema(responses=DeviceProfileDetailSwagger, request_body=DeviceProfileSerializer)
    def put(self, request, pk):
        instance = get_object_or_404(DeviceProfile, pk=pk, tenant_id=request.user.tenant_id)
        serializer = DeviceProfileSerializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(tenant_id=request.user.tenant_id)
        return Response(serializer.data)
