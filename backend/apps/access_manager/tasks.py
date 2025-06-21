import time
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from celery import shared_task
from celery.utils.log import get_task_logger

from access_manager.models import Group
from access_manager.utilits.need_sync import need_sync
from access_manager.views.staff_card import prepare_cards
from core.rabbitmq.config import connect_to_rabbitmq, send_to_rabbitmq
from core.utils.str_to_dict import str_to_dict
from main.models import Device, PublicSpace
from access_manager.utilits.batch_cards import batch_cards
from shuttle.models import Relation, RPCMessage

logger = get_task_logger(__name__)


def card_room(group_id, room_id, action, card_num=None):
    try:
        result = manage_cards_for_room_task.delay(str(group_id), str(room_id), action, card_num=card_num)
        print(f"Connect/Disconect task result: {result}")
    except Exception as e:
        print(f"Error connecting cards to room: {str(e)}")


def card_public_space(group_id, public_space_id, action, card_num=None):
    try:
        result = manage_cards_for_public_space_task.delay(str(group_id), str(public_space_id), action,
                                                          card_num=card_num)
        print(f"Connect/Disconect public space task result: {result}")
    except Exception as e:
        print(f"Error connecting cards to public space: {str(e)}")


@shared_task(autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 60})
def manage_cards_for_room_task(group_id: str, room_id: str, action: str, card_num=None):
    """Connect or disconnect cards to/from room devices."""
    try:
        cards, group = Group.objects.get_staff_cards(group_id)
        cards = [card_num] if card_num else cards
        if not cards or not group:
            return {"success": False, "message": f"No cards found for group {group_id}"}

        devices = Device.objects.filter(
            room__id=room_id,
            tenant=group.tenant,
            is_active=True
        )

        if not devices.exists():
            return {"success": False, "message": f"No active devices found for room {room_id} in tenant {group.tenant}"}

        results = process_devices_parallel(devices, cards, group, action)

        return {
            "success": True,
            "message": f"{action.capitalize()}ed {len(cards)} cards to/from {devices.count()} devices",
            "results": results
        }

    except Group.DoesNotExist:
        return {"success": False, "message": f"Group {group_id} not found or not active"}
    except Exception as e:
        raise e


@shared_task(autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 60})
def manage_cards_for_public_space_task(group_id: str, public_space_id: str, action: str, card_num=None):
    """Connect or disconnect cards to/from public space device."""
    try:
        cards, group = Group.objects.get_staff_cards(group_id)
        cards = [card_num] if card_num else cards
        if not cards or not group:
            return {"success": False, "message": f"No cards found for group {group_id}"}

        try:
            public_space = PublicSpace.objects.get(id=public_space_id)
        except PublicSpace.DoesNotExist:
            logger.error("Public space '%s' not found in tenant '%s'", public_space_id, group.tenant)
            return {"success": False, "message": f"Public space {public_space_id} not found in tenant {group.tenant}"}

        if not public_space.device or not public_space.device.is_active:
            logger.info("No device assigned to public space '%s'", public_space_id)
            return {"success": False,
                    "message": f"No device assigned to public space {public_space_id} or it is not active"}

        devices = [public_space.device]
        results = process_devices_parallel(devices, cards, group, action)

        logger.info(
            "Completed manage_cards_for_public_space_task for group '%s' and public space '%s' with action '%s'",
            group_id, public_space_id, action)

        return {
            "success": True,
            "message": f"{action.capitalize()}ed {len(cards)} cards to/from public space device",
            "results": results
        }

    except Group.DoesNotExist:
        logger.debug("Group '%s' not found or not active", group_id)
        return {"success": False, "message": f"Group {group_id} not found or not active"}
    except Exception as e:
        logger.error("Error in manage_cards_for_public_space_task: '%s'", str(e))
        raise e


def process_devices_parallel(devices, cards: List[str], group: Group, action: str) -> List[Dict[str, Any]]:
    """Process multiple devices in parallel, but process cards sequentially for each device."""
    results = []

    with ThreadPoolExecutor(max_workers=min(len(devices), 10)) as executor:
        future_to_device = {
            executor.submit(process_device_sequential, device, cards, group, action): device
            for device in devices
        }

        for future in as_completed(future_to_device):
            device = future_to_device[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                results.append({
                    "device_id": str(device.id),
                    "device_name": device.name,
                    "result": {"success": False, "error": str(e)}
                })

    return results


def process_device_sequential(device: Device, cards: List[str], group: Group, action: str) -> Dict[str, Any]:
    """Process cards for a single device sequentially in batches."""
    card_batches = batch_cards(cards)
    batch_results = []

    for i, card_batch in enumerate(card_batches):
        logger.info(
            f"Processing batch {i + 1}/{len(card_batches)} with {len(card_batch)} cards for device {device.name}")

        rpc_params = prepare_cards(card_batch, group, connect=(action == "connect"))
        result = send_card_rpc_request(device, rpc_params, card_batch, action)
        batch_results.append(result)

    return {
        "device_id": str(device.id),
        "device_name": device.name,
        "result": {
            "success": all(r.get("success", False) for r in batch_results),
            "batches_processed": len(card_batches),
            "batch_results": batch_results
        }
    }


def send_card_rpc_request(device: Device, rpc_params: List[dict], cards: List[str], action: str = "connect") -> dict:
    try:
        relation = Relation.objects.filter(to_id_id=device.id).order_by("updated_at").last()
        device_id = relation.from_id.id if relation else None
        gateway_or_none = Device.objects.gateway_or_none(device.id)  # pyright:ignore
        rpc_message = RPCMessage.objects.create(additional_info={})
        request_id = rpc_message.id

        message = {
            "targetDeviceUUID": (gateway_or_none and str(gateway_or_none.id)) or str(device_id),
            "topic": "v1/gateway/rpc",
            "data": {
                "device": str(device.name),
                "data": {"id": request_id, "method": "writeRFID", "params": rpc_params, "timeout": 10000},
            },
        }

        if not rpc_params:
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
                    print(message)
                    return {
                        "success": True,
                        "message": f"Successfully {action}ed {len(cards)} cards to/from device {device.name}"
                    }
                else:
                    print(has_message)
                    need_sync(cards, device, message)
                    return {
                        "success": False,
                        "message": f"Device {device.name} rejected card {action} request - added to sync queue"
                    }
            time.sleep(0.5)

        need_sync(cards, device, message)
        return {
            "success": False,
            "message": f"Timeout waiting for response from device {device.name} - added to sync queue"
        }

    except Exception as e:
        need_sync(cards, device, message)
        return {
            "success": False,
            "message": f"Error sending RPC {action} request to device {device.name}: {str(e)} - added to sync queue"
        }
