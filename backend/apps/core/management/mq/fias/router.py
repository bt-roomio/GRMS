import logging

from core.management.mq.fias.constants import KEY_COMMANDS
from core.management.mq.fias.handlers.keydatachange import handle_keydatachange
from core.management.mq.fias.handlers.keydelete import handle_keydelete
from core.management.mq.fias.handlers.keyread import handle_keyread
from core.management.mq.fias.handlers.keyrequest import handle_keyrequest
from core.management.mq.fias.handlers.reservation import handle_reservation
from core.management.mq.fias.utils.rpc import send_card_operation_confirmation

logger = logging.getLogger(__name__)

KEY_COMMAND_HANDLERS = {
    "keyrequest": handle_keyrequest,
    "keydelete": handle_keydelete,
    "keydatachange": handle_keydatachange,
    "keyread": handle_keyread,
}


def handle_fias(data, device):
    logger.info("Handling FIAS data: %s", data)
    command = data.get("command")

    if command in KEY_COMMANDS:
        _dispatch_key_command(command, data, device)
        return

    handle_reservation(command, data, device)


def _dispatch_key_command(command, data, device):
    operation_id = data.get("operationId")
    if not operation_id:
        logger.error("Missing operationId for command=%s", command)
        return

    try:
        KEY_COMMAND_HANDLERS[command](data, device)
    except Exception as exc:
        logger.exception(
            "Error handling FIAS key command=%s operationId=%s: %s",
            command,
            operation_id,
            exc,
        )
        send_card_operation_confirmation(device, operation_id, status="UR", text=str(exc))
