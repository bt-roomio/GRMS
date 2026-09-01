import logging

from django.core.exceptions import ValidationError
from hoteza.serializers.checkin import CheckInSerializer
from hoteza.serializers.checkout import CheckOutSerializer

from core.management.mq.fias.handlers.datachange import handle_datachange
from core.management.mq.fias.utils.guests import override_checkout_time
from core.management.mq.fias.utils.payloads import build_reservation_payload

logger = logging.getLogger(__name__)

_SERIALIZERS = {
    "checkin": CheckInSerializer,
    "checkout": CheckOutSerializer,
}


def handle_reservation(command, data, device):
    """Entry point for every FIAS command that is not a key command."""
    if command == "datachange":
        return handle_datachange(data, device)

    serializer_cls = _SERIALIZERS.get(command)
    if serializer_cls is None:
        raise ValidationError(f"Invalid command: {command}")

    mapped = build_reservation_payload(command, data, device)
    if command == "checkin":
        mapped["departureDateTS"] = override_checkout_time(mapped["tenantId"], mapped["departureDateTS"])

    serializer = serializer_cls(data=mapped)

    # Caught broadly on purpose: DRF raises rest_framework's ValidationError and hoteza
    # raises JsonValidationError (an APIException) — neither is Django's ValidationError,
    # so an `except ValidationError` here would never match and would fall through to
    # serializer.save() on an unvalidated serializer.
    try:
        serializer.is_valid(raise_exception=True)
    except Exception as e:
        logger.error("Invalid %s payload: %s", command, e)
        raise

    serializer.save()
