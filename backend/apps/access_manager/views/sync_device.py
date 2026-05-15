import time

from access_manager.models import NeedSyncDevice
from access_manager.serializers.need_sync import (
    NeedSyncDeviceHttpFilterParams,
    SimpleNeedSyncDeviceSerializer,
    SyncDeviceSerializer,
)
from access_manager.swagger.sync_device import (
    sync_device_delete_by_device_swagger,
    sync_device_delete_swagger,
    sync_device_get_swagger,
    sync_device_swagger,
)
from access_manager.tasks.sync_device import sync_devices_task
from access_manager.utilits.card_user import get_card_user
from celery.utils.log import get_task_logger

from rest_framework.fields import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from main.models import Device

logger = get_task_logger(__name__)


class SyncDeviceByDeviceDetailView(APIView):
    @sync_device_delete_by_device_swagger()
    def delete(self, request, device_id):
        instances = NeedSyncDevice.objects.filter(device_id=device_id, need_sync=True)
        if not instances:
            raise ValidationError("Any need sync device not found!")

        removed_sync = 0
        for instance in instances:
            instance.need_sync = False
            instance.save()
            removed_sync += 1

        return Response({"removed_sync": removed_sync})


class SyncDeviceDetailView(APIView):
    @sync_device_delete_swagger()
    def delete(self, request, pk):
        instance = get_object_or_404(NeedSyncDevice, pk=pk)
        if not instance.need_sync:
            raise ValidationError("Device is already syncing")
        instance.need_sync = False
        instance.save()
        return Response()


class SyncDeviceView(APIView):
    @sync_device_get_swagger()
    def get(self, request):
        params = NeedSyncDeviceHttpFilterParams.check(request.GET)
        queryset = Device.objects.get_card_related_devices(
            params.get("card_id"), params.get("need_sync", None)
        )
        if not queryset.exists():
            return Response({"message": "No devices need syncing"}, status=200)

        holder = get_card_user(params.get("card_id"))
        serializer = SimpleNeedSyncDeviceSerializer(
            queryset,
            many=True,
            context={"holder": holder, "card_id": params.get("card_id")},
        )
        return Response(serializer.data, 200)

    @sync_device_swagger()
    def post(self, request):
        serializer = SyncDeviceSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "success": False,
                    "message": "Invalid request data",
                    "errors": serializer.errors,
                },
                status=400,
            )

        ids = serializer.validated_data.get("ids", [])  # pyright: ignore
        device_ids = serializer.validated_data.get("device_ids", [])  # pyright: ignore
        tenant_id = request.user.tenant_id

        need_sync_exists = NeedSyncDevice.objects.check_avialibility(
            tenant_id, ids=ids, device_ids=device_ids
        )

        if not need_sync_exists:
            return Response(
                {"success": True, "message": "No devices need syncing"}, status=200
            )

        sync_devices_task.delay(tenant_id, ids, device_ids)

        time.sleep(3)
        return Response(
            {"success": True, "message": "Device sync task started successfully"},
            status=202,
        )
