import logging
import time

from celery import shared_task

from access_manager.utilits.card_activate import (
    activate_guest_card,
    activate_staff_card,
)
from access_manager.utilits.card_deactivate import (
    deactivate_guest_card,
    deactivate_staff_card,
)
from access_manager.utilits.need_sync import need_sync
from access_manager.utilits.prepare_rpc_request import prepare_rpc_request
from core.rabbitmq.config import connect_to_rabbitmq, send_to_rabbitmq
from core.utils.str_to_dict import str_to_dict
from shuttle.models import RPCMessage

logger = logging.getLogger(__name__)
TIMEOUT = 10


@shared_task(autoretry_for=(Exception,), retry_kwargs={"max_retries": 3, "countdown": 60})
def send_rpc_request(device_id, cards, access, user=None, guest_id=None, staff_id=None, sync=False, is_pwd=False):
    request_params = prepare_rpc_request(device_id, cards, access, guest_id, staff_id, is_pwd=is_pwd)

    message = request_params.get("message")
    request_id = request_params.get("request_id")
    room_number = request_params.get("room_number")
    public_spaces = request_params.get("public_spaces")
    staff = request_params.get("staff")
    guest = request_params.get("guest")
    device = request_params.get("device")
    fail_response = request_params.get("fail_response")

    if not cards:
        logger.info("Cards are not provided ! ")
        return {
            "success": True,
            "cards_empty": True,
            "message": "Cards are not provided ! ",
        }

    if device and not device.status:
        need_sync(cards, device, access, user=user, reason="Device is not connected")
        fail_response.update({"success": False, "message": "Device is not connected !"})
        logger.info("Device is not connected ! ")
        return fail_response

    channel = connect_to_rabbitmq()
    logger.info(f"Message: {message}")
    send_to_rabbitmq(channel, message)

    start_time = time.time()

    while time.time() - start_time < TIMEOUT:
        has_message = RPCMessage.objects.filter(id=request_id, received=True).first()
        is_success = str_to_dict(has_message.additional_info).get("success") if has_message else False
        if has_message and access == 0:
            if is_success:
                result = deactivate_staff_card(staff) if staff_id else deactivate_guest_card(cards, device, sync)
                result.update({"room": room_number, "public_spaces": public_spaces})
                return result
            not sync and need_sync(
                cards,
                device,
                access,
                user=user,
                reason="Device rejected the deactivation request",
            )
            return fail_response

        elif has_message and is_success and access != 0:
            if sync:
                return {
                    "success": True,
                    "message": "Operation is passed successfully! ",
                }
            result = (
                activate_staff_card(cards, staff, device)
                if staff_id
                else activate_guest_card(cards, device, guest, is_pwd=is_pwd)
            )
            result.update({"room": room_number, "public_spaces": public_spaces})
            return result

        time.sleep(1)
    else:
        not sync and need_sync(
            cards,
            device,
            access,
            user=user,
            reason="No response from device within timeout",
        )
        fail_response.update({"message": "Time out error!"})
        return fail_response
