import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List

from access_manager.models import NeedSyncDevice
from access_manager.serializers.need_sync import (
    NeedSyncDeviceHttpFilterParams,
    SimpleNeedSyncDeviceSerializer,
    SyncDeviceSerializer,
)
from access_manager.swagger.sync_device import sync_device_delete_swagger, sync_device_get_swagger, sync_device_swagger
from celery import shared_task
from celery.utils.log import get_task_logger
from django.db.models import Prefetch

from rest_framework import status
from rest_framework.fields import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from core.rabbitmq.config import connect_to_rabbitmq, send_to_rabbitmq
from core.utils.str_to_dict import str_to_dict
from main.models import DevicePublicSpaces
from shuttle.models import RPCMessage

logger = get_task_logger(__name__)


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
    from drf_yasg import openapi
    from drf_yasg.utils import swagger_auto_schema

    @sync_device_get_swagger()
    def get(self, request):
        params = NeedSyncDeviceHttpFilterParams.check(request.GET)
        queryset = (
            NeedSyncDevice.objects.select_related("device__tenant", "device__room")
            .prefetch_related(
                Prefetch(
                    "device__device_public_spaces",
                    queryset=DevicePublicSpaces.objects.select_related("public_space"),
                    to_attr="prefetched_device_public_spaces",
                )
            )
            .filter(
                need_sync=True,
                card_id=params.get("card_id"),
            )
        )
        if not queryset.exists():
            raise Exception("Not found any devices need syncing")

        first = queryset.first()
        holder_type, holder_name = first.get_card_holder_name if first else (None, None)
        serializer = SimpleNeedSyncDeviceSerializer(
            queryset, many=True, context={"holder": {"type": holder_type, "name": holder_name}}
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
                status=status.HTTP_400_BAD_REQUEST,
            )

        ids = serializer.validated_data.get("ids", [])  # pyright: ignore
        device_ids = serializer.validated_data.get("device_ids", [])  # pyright: ignore
        tenant_id = request.user.tenant_id

        # Check if any devices need syncing based on provided filters
        queryset = NeedSyncDevice.objects.filter(need_sync=True, device__tenant_id=tenant_id)

        if ids:
            queryset = queryset.filter(id__in=ids)
        elif device_ids:
            queryset = queryset.filter(device_id__in=device_ids)

        need_sync_exists = queryset.exists()

        if not need_sync_exists:
            return Response(
                {
                    "success": True,
                    "message": "No devices need syncing",
                },
                status=status.HTTP_200_OK,
            )

        sync_devices_task.delay(tenant_id, ids, device_ids)

        return Response(
            {
                "success": True,
                "message": "Device sync task started successfully",
            },
            status=status.HTTP_202_ACCEPTED,
        )


@shared_task(autoretry_for=(Exception,), retry_kwargs={"max_retries": 3, "countdown": 60})
def sync_devices_task(tenant_id, ids=None, device_ids=None):
    try:
        queryset = NeedSyncDevice.objects.select_related("device", "card").filter(
            need_sync=True, device__status=True, device__is_active=True, device__tenant_id=tenant_id
        )
        if ids:
            queryset = queryset.filter(id__in=ids)
        elif device_ids:
            queryset = queryset.filter(device_id__in=device_ids)

        need_sync_objects = queryset.all()

        device_groups = defaultdict(list)
        for sync_obj in need_sync_objects:
            device_groups[sync_obj.device].append(sync_obj)

        if not device_groups:
            return {
                "success": True,
                "message": "No active devices need syncing",
                "synced_count": 0,
                "unsuccessful_messages": [],
            }

        results = process_devices_parallel(device_groups)

        total_synced = sum(result.get("synced_count", 0) for result in results)
        total_unsuccessful = []
        for result in results:
            total_unsuccessful.extend(result.get("unsuccessful_messages", []))

        final_result = {
            "success": len(total_unsuccessful) == 0,
            "message": (
                f"Successfully synced {total_synced} devices"
                if not total_unsuccessful
                else f"Synced {total_synced} devices with {len(total_unsuccessful)} errors"
            ),
            "unsuccessful_messages": total_unsuccessful,
            "synced_count": total_synced,
        }

        logger.info("Sync task completed: %s", final_result["message"])
        return final_result

    except Exception as e:
        logger.error("Error in sync_devices_task: %s", str(e))
        raise e


def process_devices_parallel(device_groups: Dict) -> List[Dict[str, Any]]:
    results = []

    with ThreadPoolExecutor(max_workers=min(len(device_groups), 10)) as executor:
        future_to_device = {
            executor.submit(process_device_sequential, device, sync_objects): device
            for device, sync_objects in device_groups.items()
        }

        for future in as_completed(future_to_device):
            device = future_to_device[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger.error("Error processing device %s: %s", device.name, str(e))
                results.append(
                    {
                        "device_name": device.name,
                        "synced_count": 0,
                        "unsuccessful_messages": [
                            {"device": device.name, "card": "Unknown", "message": "Processing error", "error": str(e)}
                        ],
                    }
                )

    return results


def process_device_sequential(device, sync_objects: List) -> Dict[str, Any]:
    """Process sync objects for a single device sequentially in batches of 10."""
    synced_count = 0

    batch_size = 10
    batches = [sync_objects[i : i + batch_size] for i in range(0, len(sync_objects), batch_size)]

    logger.info("Processing %d batches for device %s", len(batches), device.name)

    for batch_num, batch in enumerate(batches, 1):
        logger.info(
            "Processing batch %d/%d with %d requests for device %s", batch_num, len(batches), len(batch), device.name
        )

        batch_params = []
        batch_sync_objects = []

        for sync_obj in batch:
            additional_info = sync_obj.additional_info or {}
            failed_request = additional_info.get("failed_request")

            if not failed_request:
                sync_obj.need_sync = False
                sync_obj.save()
                synced_count += 1
                logger.info(
                    "Device %s sync object %s has no failed requests, marked as synced", device.name, sync_obj.id
                )
                continue

            request_params = failed_request.get("data", {}).get("data", {}).get("params", [])
            batch_params.extend(request_params)
            batch_sync_objects.append(sync_obj)

        if not batch_params:
            logger.info("No parameters to send for batch %d of device %s", batch_num, device.name)
            continue

        result = send_batch_rpc_request(device, batch_params, batch_sync_objects)

        if result.get("success"):
            for sync_obj in batch_sync_objects:
                sync_obj.need_sync = False
                sync_obj.save()
                synced_count += 1
            logger.info("Successfully processed batch %d for device %s", batch_num, device.name)
        else:
            logger.warning(
                "Failed to process batch %d for device %s: %s", batch_num, device.name, result.get("message")
            )

    return {
        "device_name": device.name,
        "synced_count": synced_count,
    }


def send_batch_rpc_request(device, batch_params: List[dict], sync_objects: List) -> dict:
    """Send a batch RPC request with multiple parameters."""
    try:
        # Create RPC message for batch request
        rpc_message = RPCMessage.objects.create(additional_info={})
        request_id = rpc_message.id

        # Get device info (similar to tasks.py logic)
        from main.models import Device
        from shuttle.models import Relation

        relation = Relation.objects.filter(to_id_id=device.id).order_by("updated_at").last()
        device_id = relation.from_id.id if relation else None
        gateway_or_none = Device.objects.filter(pk=device.id, additional_info__gateway=True, is_active=True).first()

        message = {
            "targetDeviceUUID": (gateway_or_none and str(gateway_or_none.id)) or str(device_id),
            "topic": "v1/gateway/rpc",
            "data": {
                "device": str(device.name),
                "data": {"id": request_id, "method": "writeRFID", "params": batch_params, "timeout": 10000},
            },
        }

        logger.info(
            "Sending batch RPC request with ID: %s for device %s with %d parameters",
            request_id,
            device.name,
            len(batch_params),
        )

        channel = connect_to_rabbitmq()
        send_to_rabbitmq(channel, message)

        timeout_seconds = 10
        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            has_message = RPCMessage.objects.filter(id=request_id, received=True).first()
            if has_message:
                success = bool(str_to_dict(has_message.additional_info).get("success"))
                logger.info(
                    "Batch RPC request %s for device %s completed with success: %s", request_id, device.name, success
                )
                return {
                    "success": success,
                    "message": (
                        f"Batch RPC request completed for device {device.name}"
                        if success
                        else f"Batch RPC request failed for device {device.name}"
                    ),
                }
            time.sleep(0.5)

        logger.warning(
            "Batch RPC request %s for device %s timed out after %d seconds", request_id, device.name, timeout_seconds
        )
        return {"success": False, "message": f"Timeout waiting for RPC response from device {device.name}"}

    except Exception as e:
        logger.error("Error sending batch RPC request for device %s: %s", device.name, str(e))
        return {"success": False, "message": f"Error sending batch RPC request to device {device.name}: {str(e)}"}
