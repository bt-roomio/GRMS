import time

from access_manager.models import NeedSyncDevice

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from access_manager.serializers.need_sync import SyncDeviceSerializer
from access_manager.swagger.sync_device import sync_device_swagger
from core.rabbitmq.config import connect_to_rabbitmq, send_to_rabbitmq
from core.utils.str_to_dict import str_to_dict
from shuttle.models import RPCMessage
from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


class SyncDeviceView(APIView):
    
    @sync_device_swagger()
    def post(self, request):
        serializer = SyncDeviceSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "success": False,
                "message": "Invalid request data",
                "errors": serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        ids = serializer.validated_data.get('ids', [])
        tenant_id = request.user.tenant_id

        need_sync_exists = NeedSyncDevice.objects.filter(
            need_sync=True, device__tenant_id=tenant_id,
            id__in=ids).exists() if ids else NeedSyncDevice.objects.filter(
            need_sync=True, device__tenant_id=tenant_id
        ).exists()

        if not need_sync_exists:
            return Response({
                "success": True,
                "message": "No devices need syncing",
            }, status=status.HTTP_200_OK)

        sync_devices_task.delay(tenant_id, ids)

        return Response({
            "success": True,
            "message": "Device sync task started successfully",
        }, status=status.HTTP_202_ACCEPTED)


@shared_task(autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 60})
def sync_devices_task(tenant_id, ids=None):
    try:
        unsuccessful_messages = []
        synced_count = 0
        queryset = NeedSyncDevice.objects.select_related('device', 'card').filter(
            need_sync=True,
            device__tenant_id=tenant_id
        )
        if ids:
            queryset = queryset.filter(id__in=ids)
        need_sync_objects = queryset.all()

        for sync_obj in need_sync_objects:
            print(sync_obj.id)
            try:
                additional_info = sync_obj.additional_info or {}
                failed_requests = additional_info.get("failed_requests", [])

                if not failed_requests:
                    sync_obj.need_sync = False
                    sync_obj.save()
                    synced_count += 1
                    logger.info("Device %s has no failed requests, marked as synced", sync_obj.device.name)
                    continue

                for num in reversed(range(len(failed_requests))):
                    request_message = failed_requests[num]
                    logger.info("Processing failed request %d for device %s", num, sync_obj.device.name)

                    result = send_rpc_request(request_message)

                    if result.get("success"):
                        failed_requests.pop(num)
                        logger.info("Successfully processed request for device %s", sync_obj.device.name)
                    else:
                        logger.warning("Failed to process request for device %s: %s", sync_obj.device.name,
                                       result.get("message"))
                        unsuccessful_messages.append({
                            "device": sync_obj.device.name,
                            "card": sync_obj.card.number if sync_obj.card else "Unknown",
                            "message": request_message,
                            "error": result.get("message", "Unknown error")
                        })

                if not failed_requests:
                    sync_obj.need_sync = False
                    synced_count += 1
                    logger.info("All requests processed successfully for device %s", sync_obj.device.name)
                else:
                    logger.warning("Some requests still failed for device %s", sync_obj.device.name)

                sync_obj.additional_info = additional_info
                sync_obj.save()

            except Exception as e:
                logger.error("Error processing sync object %s: %s", sync_obj.id, str(e))
                unsuccessful_messages.append({
                    "device": sync_obj.device.name if sync_obj.device else "Unknown",
                    "card": sync_obj.card.number if sync_obj.card else "Unknown",
                    "message": "Processing error",
                    "error": str(e)
                })

        result = {
            "success": len(unsuccessful_messages) == 0,
            "message": f"Successfully synced {synced_count} devices" if not unsuccessful_messages else f"Synced {synced_count} devices with {len(unsuccessful_messages)} errors",
            "unsuccessful_messages": unsuccessful_messages,
            "synced_count": synced_count,
        }

        logger.info("Sync task completed: %s", result["message"])
        return result

    except Exception as e:
        logger.error("Error in sync_devices_task: %s", str(e))
        raise e


def send_rpc_request(message):
    try:
        request_id = message.get("data", {}).get("data", {}).get("id")
        logger.info("Sending RPC request with ID: %s", request_id)

        channel = connect_to_rabbitmq()
        send_to_rabbitmq(channel, message)

        timeout_seconds = 10
        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            has_message = RPCMessage.objects.filter(id=request_id, received=True).first()
            if has_message:
                success = bool(str_to_dict(has_message.additional_info).get("success"))
                logger.info("RPC request %s completed with success: %s", request_id, success)
                return {
                    "success": success,
                    "message": "RPC request completed" if success else "RPC request failed"
                }
            time.sleep(0.5)

        logger.warning("RPC request %s timed out after %d seconds", request_id, timeout_seconds)
        return {
            "success": False,
            "message": "Timeout waiting for RPC response"
        }

    except Exception as e:
        logger.error("Error sending RPC request: %s", str(e))
        return {
            "success": False,
            "message": f"Error sending RPC request: {str(e)}"
        }
