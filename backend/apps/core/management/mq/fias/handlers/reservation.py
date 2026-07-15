import logging

from django.core.exceptions import ValidationError
from hoteza.serializers.checkin import CheckInSerializer
from hoteza.serializers.checkout import CheckOutSerializer

from core.management.mq.fias.utils.guests import apply_auto_checkout
from core.management.mq.fias.utils.payloads import build_reservation_payload
from main.models import Guest

logger = logging.getLogger(__name__)

_SERIALIZERS = {
    "checkin": CheckInSerializer,
    "checkout": CheckOutSerializer,
}


def handle_reservation(command, data, device):
    serializer_cls = _SERIALIZERS.get(command)
    if serializer_cls is None:
        raise ValidationError("Invalid command")

    mapped = build_reservation_payload(command, data, device)
    serializer = serializer_cls(data=mapped)

    try:
        serializer.is_valid(raise_exception=True)
    except ValidationError as e:
        logger.error(e)
    except Exception as e:
        logger.error("Request data: %s", e)
        raise
    instance = serializer.save()

    if command == "checkin" and isinstance(instance, Guest):
        apply_auto_checkout(instance)
