from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from access_manager.models import NeedSyncDevice
from core.utils.pagination import pagination
from core.utils.permission import check_perms
from main.models import Device, DevicePublicSpaces, Room
from main.serializers.device import DeviceFilterParams, DeviceSerializer
from main.swagger.device import DeviceDetailSwagger, DeviceSwagger


class DeviceListView(APIView):
    @swagger_auto_schema(tags=["Main, Device"], responses=DeviceSwagger, query_serializer=DeviceFilterParams())
    @check_perms(["main.view_device"])
    def get(self, request):
        params = DeviceFilterParams.check(request.GET)
        queryset = Device.objects.list(
            tenant=request.user.tenant,
            search_field=params.get("search_field"),  # pyright: ignore
            search_value=params.get("search_value"),  # pyright: ignore
            status=params.get("status"),  # pyright: ignore
            sort_by=params.get("sort_by"),  # pyright: ignore
            name=params.get("name"),
            device_profile=params.get("device_profile"),
        )
        serializer = DeviceSerializer(queryset, many=True)
        data = pagination(queryset, serializer, params.get("page"), params.get("size"))  # pyright: ignore
        return Response(data)

    @swagger_auto_schema(tags=["Main, Device"], responses=DeviceSwagger, request_body=DeviceSerializer)
    @check_perms(["main.add_device"])
    def post(self, request):
        tenant_id = request.user.tenant_id
        data = request.data.copy()
        data["tenant"] = tenant_id
        serializer = DeviceSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(tenant_id=tenant_id)
        return Response(serializer.data, 201)


class DeviceDetailView(APIView):
    @swagger_auto_schema(tags=["Main, Device"], responses=DeviceDetailSwagger)
    @check_perms(["main.view_device"])
    def get(self, request, pk):
        queryset = Device.objects.select_related("device_profile", "credentials").filter(is_active=True)
        device = get_object_or_404(queryset, pk=pk, tenant_id=request.user.tenant_id)
        serializer = DeviceSerializer(device)
        return Response(serializer.data)

    @swagger_auto_schema(tags=["Main, Device"], responses=DeviceDetailSwagger, request_body=DeviceSerializer)
    @check_perms(["main.change_device"])
    def put(self, request, pk):
        device = get_object_or_404(Device, pk=pk, tenant_id=request.user.tenant_id, is_active=True)
        serializer = DeviceSerializer(device, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(tenant_id=request.user.tenant_id)
        return Response(serializer.data)

    @swagger_auto_schema(tags=["Main, Device"], responses={})
    @check_perms(["main.delete_device"])
    def delete(self, request, pk):
        device = get_object_or_404(Device, pk=pk, tenant_id=request.user.tenant_id, is_active=True)
        remove_need_sync(device)
        device.is_active = False
        device.save()
        return Response({}, 204)


def remove_need_sync(device: Device):
    NeedSyncDevice.objects.filter(device=device, need_sync=True).update(need_sync=False)
    DevicePublicSpaces.objects.filter(device=device).delete()
    Room.objects.filter(door_lock_device=device).update(door_lock_device=None)

    if device.room:
        device.room = None
        device.save()
