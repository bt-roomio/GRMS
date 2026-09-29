from core.management.mq.fias.handlers.checkinout import handle_checkin_checkout
from core.management.mq.fias.handlers.datachange import handle_datachange


def handle_reservation(command, data, device):
    """Entry point for every FIAS command that is not a key command."""
    if command == "datachange":
        return handle_datachange(data, device)

    handle_checkin_checkout(command, data, device)
