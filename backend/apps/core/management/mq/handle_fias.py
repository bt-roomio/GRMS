import logging

from django.core.exceptions import ValidationError
from hoteza.serializers.checkin import CheckInSerializer
from hoteza.serializers.checkout import CheckOutSerializer

logger = logging.getLogger(__name__)


def handle_fias(data, device):
    logger.debug("Handling FIAS data: %s", data)
    tenant_id = device.get("tenant_id")
    data = {
        "command": data.get("command"),
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
        "swapFlag": data.get("swapFlag", "swapFlag"),
        "nopost": data.get("nopost", "nopost"),
        "profileNum": data.get("profileNum", "profileNum"),
    }

    if data.get("command") == "checkin":
        serializer = CheckInSerializer(data=data)
    elif data.get("command") == "checkout":
        serializer = CheckOutSerializer(data=data)
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
