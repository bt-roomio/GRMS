import logging

from django.core.exceptions import ValidationError
from hoteza.serializers.checkin import CheckInSerializer
from hoteza.serializers.checkout import CheckOutSerializer

from core.rabbitmq.config import connect_to_rabbitmq, send_to_rabbitmq

logger = logging.getLogger(__name__)

KEY_COMMANDS = {"keyrequest", "keydelete", "keydatachange", "keyread"}

KEY_COMMAND_TEXTS = {
    "keyrequest": "Key request processed successfully",
    "keydelete": "Key deleted successfully",
    "keydatachange": "Key data change processed successfully",
    "keyread": "Key read processed successfully",
}


def _send_card_operation_confirmation(device, operation_id, status="OK", text=""):
    """Send RPC confirmCardOperation response back to gateway via RabbitMQ."""
    device_id = device.get("id")
    message = {
        "targetDeviceUUID": str(device_id),
        "topic": "v1/gateway/rpc",
        "data": {
            "method": "confirmCardOperation",
            "params": {
                "operationId": operation_id,
                "status": status,
                "text": text,
            },
        },
    }
    try:
        ch = connect_to_rabbitmq()
        send_to_rabbitmq(ch, message, routing_key="fromGRMS")
        ch.connection.close()
        logger.info("Sent confirmCardOperation for operationId=%s status=%s", operation_id, status)
    except Exception as exc:
        logger.exception("Failed to send confirmCardOperation for operationId=%s: %s", operation_id, exc)
        raise


def _send_attribute(device):
    device_id = device.get("id")
    message = {
        "targetDeviceUUID": str(device_id),
        "topic": "v1/gateway/rpc",
        "data": {
            "method": "",
            "params": {},
        },
    }
    try:
        ch = connect_to_rabbitmq()
        send_to_rabbitmq(ch, message, routing_key="fromGRMS")
        ch.connection.close()
        logger.info("Sent attribute for device=%s", device_id)
    except Exception as exc:
        logger.exception("Failed to send attribute %s", exc)
        raise


def handle_fias(data, device):
    logger.info("Handling FIAS data: %s", data)
    command = data.get("command")

    if command in KEY_COMMANDS:
        operation_id = data.get("operationId")
        if not operation_id:
            logger.error("Missing operationId for command=%s", command)
            return
        text = KEY_COMMAND_TEXTS.get(command, "Processed successfully")
        _send_card_operation_confirmation(device, operation_id, status="OK", text=text)
        return

    tenant_id = device.get("tenant_id")
    mapped = {
        "command": command,
        "tenantId": str(tenant_id),
        "roomNumber": data.get("roomName", "roomNumber"),
        "guestName": data.get("guestName", "guestName"),
        "guestFirstName": data.get("guestFirstName", "guestFirstName"),
        "guestTitle": data.get("guestTitle", "guestTitle"),
        "pmsRegNum": data.get("reservationNumber", "pmsRegNum"),
        "arrivalDateTS": data.get("checkInDate", "arrivalDateTS"),
        "departureDateTS": data.get("checkOutDate", "departureDateTS"),
        "guestLanguage": data.get("language", "guestLanguage"),
        "roomShare": 1 if data.get("shareFlag", "roomShare") else 0,
        "swapFlag": data.get("swapFlag", 0),
        "nopost": data.get("nopost", "nopost"),
        "profileNum": data.get("profileNum", "profileNum"),
    }

    if command == "checkin":
        serializer = CheckInSerializer(data=mapped)
    elif command == "checkout":
        serializer = CheckOutSerializer(data=mapped)
    else:
        raise ValidationError("Invalid command")

    try:
        serializer.is_valid(raise_exception=True)
    except ValidationError as e:
        logger.error(e)
    except Exception as e:
        logger.error("Request data: %s", e)
        raise
    serializer.save()
