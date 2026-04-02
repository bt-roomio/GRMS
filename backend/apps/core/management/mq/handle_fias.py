import logging

from django.core.exceptions import ValidationError
from hoteza.serializers.checkin import CheckInSerializer
from hoteza.serializers.checkout import CheckOutSerializer

from core.management.mq.fias_key_handler import KEY_COMMAND_HANDLERS, KEY_COMMANDS, send_card_operation_confirmation

logger = logging.getLogger(__name__)


def handle_fias(data, device):
    logger.info("Handling FIAS data: %s", data)
    command = data.get("command")

    if command in KEY_COMMANDS:
        operation_id = data.get("operationId")
        if not operation_id:
            logger.error("Missing operationId for command=%s", command)
            return
        try:
            handler = KEY_COMMAND_HANDLERS[command]
            handler(data, device)
        except Exception as exc:
            logger.exception("Error handling FIAS key command=%s operationId=%s: %s", command, operation_id, exc)
            send_card_operation_confirmation(device, operation_id, status="UR", text=str(exc))
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
