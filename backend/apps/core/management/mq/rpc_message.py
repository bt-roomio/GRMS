import logging

from shuttle.models import RPCMessage

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def handle_rpc(data):
    logger.debug("Handling RPC: %s", data)
    RPCMessage.objects.filter(id=data.get("id"), received=False).update(
        received=True,
        additional_info=data.get("data"),
    )
