import logging

from access_manager.tasks.send_rpc import send_rpc_request
from core.rabbitmq.config import connect_to_rabbitmq, send_to_rabbitmq
from main.models import Device
from main.utils.access_context import get_guest_access_context
from shuttle.models import Relation, RPCMessage

logger = logging.getLogger(__name__)


def _resolve_target_device_uuid(device):
    relation = Relation.objects.filter(to_id_id=device["id"]).order_by("updated_at").last()
    device_id = relation and relation.from_id.id
    gateway_or_none = Device.objects.gateway_or_none(device["id"])  # pyright: ignore
    return (gateway_or_none and str(gateway_or_none.id)) or str(device_id)


def _build_confirm_message(device, request_id, operation_id, status, text):
    return {
        "targetDeviceUUID": _resolve_target_device_uuid(device),
        "topic": "v1/gateway/rpc",
        "data": {
            "device": str(device["name"]),
            "data": {
                "id": request_id,
                "method": "confirmCardOperation",
                "params": {
                    "operationId": operation_id,
                    "status": status,
                    "text": text,
                },
            },
        },
    }


def send_card_operation_confirmation(device, operation_id, status="OK", text=""):
    rpc_message = RPCMessage.objects.create(additional_info={})
    request_id = rpc_message.id

    message = _build_confirm_message(device, request_id, operation_id, status, text)

    logger.debug("Sending confirmation message to %s", message)

    try:
        channel = connect_to_rabbitmq()
        send_to_rabbitmq(channel, message)
        channel.connection.close()

        logger.info("confirmCardOperation operationId=%s status=%s", operation_id, status)
    except Exception as exc:
        logger.exception("Failed confirmCardOperation operationId=%s: %s", operation_id, exc)
        raise


def send_rpc_to_guest_devices(guest, card_uid, access):
    context = get_guest_access_context(guest)
    devices = context.get("devices")
    if not devices:
        return False, "No devices found for guest room"

    if access == 0 and not context.get("guest_cards"):
        return True, "Operation completed"

    errors = []
    successes = []
    for dev in devices:
        result = send_rpc_request(str(dev.id), [card_uid], access, guest_id=str(guest.id))
        if result.get("success"):
            successes.append(result.get("message", "OK"))
        else:
            errors.append(result.get("message", "Failed"))

    if errors:
        return False, "; ".join(errors)
    return True, "; ".join(successes) if successes else "Operation completed"
