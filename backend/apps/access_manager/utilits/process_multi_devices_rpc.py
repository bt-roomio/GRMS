import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List

from access_manager.models import Group
from access_manager.utilits.need_sync import need_sync
from access_manager.utilits.not_need_sync import not_need_sync
from celery.utils.log import get_task_logger

from access_manager.utilits.prepare_rpc_request import prepare_rpc_request
from access_manager.utilits.remove_slots import remove_card_device_slots
from core.rabbitmq.config import connect_to_rabbitmq, send_to_rabbitmq
from core.utils.str_to_dict import str_to_dict
from main.models import Device
from shuttle.models import RPCMessage

logger = get_task_logger(__name__)


def process_devices_parallel(devices, cards: List[str], group: Group, action: str) -> List[Dict[str, Any]]:
    results = []

    with ThreadPoolExecutor(max_workers=min(len(devices), 10)) as executor:
        future_to_device = {
            executor.submit(process_device_all_cards, device, cards, group, action): device for device in devices
        }

        for future in as_completed(future_to_device):
            device = future_to_device[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                results.append(
                    {
                        "device_id": str(device.id),
                        "device_name": device.name,
                        "result": {"success": False, "error": str(e)},
                    }
                )

    return results


def process_device_all_cards(device: Device, cards: List[str], group: Group, action: str) -> Dict[str, Any]:
    access = 1 if action == "connect" else 0
    request_params = prepare_rpc_request(device.id, cards, access)
    result = send_card_rpc_request(device, request_params, cards, action)

    return {
        "device_id": str(device.id),
        "device_name": device.name,
        "result": result,
    }


def send_card_rpc_request(device: Device, request_params: dict, cards: List[str], action: str = "connect") -> dict:
    access = 1 if action == "connect" else 0
    try:
        message = request_params.get("message")
        request_id = request_params.get("request_id")
        device = request_params.get("device")

        if not cards:
            return {"success": False, "message": "No card parameters to send"}
        channel = connect_to_rabbitmq()
        send_to_rabbitmq(channel, message)

        timeout_seconds = 10
        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            has_message = RPCMessage.objects.filter(id=request_id, received=True).first()
            if has_message:
                success = bool(str_to_dict(has_message.additional_info).get("success"))
                if success:
                    not_need_sync(cards, [device])
                    action == "disconnect" and remove_card_device_slots(cards, device)
                    return {
                        "success": True,
                        "message": f"Successfully {action}ed {len(cards)} cards to/from device {device.name}",
                    }
                else:
                    need_sync(cards, device, access, reason=f"Device {device.name} rejected card {action} request")
                    return {
                        "success": False,
                        "message": f"Device {device.name} rejected card {action} request - added to sync queue",
                    }
            time.sleep(0.5)

        need_sync(cards, device, access, reason=f"Timeout waiting for response from device {device.name}")
        return {
            "success": False,
            "message": f"Timeout waiting for response from device {device.name} - added to sync queue",
        }

    except Exception as e:
        need_sync(cards, device, access, reason=f"Error sending RPC to device {device.name}: {e}")
        return {
            "success": False,
            "message": f"Error sending RPC {action} request to device {device.name}: {str(e)} - added to sync queue",
        }
