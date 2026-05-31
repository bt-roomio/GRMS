import logging

from access_manager.utilits.get_device_cards import get_device_cards

logger = logging.getLogger(__name__)


def register_cards_for_public_space(public_space_id, devices, connect):
    from access_manager.tasks.send_rpc import send_rpc_request

    try:
        for device in devices:
            try:
                cards_of_device = get_device_cards(device, [], connect)
                send_rpc_request(str(device), cards_of_device, connect, sync=True)
            except Exception as e:
                logger.error("Error registering cards for device %s : %s", device.id, str(e))
    except Exception as e:
        logger.error("Error in cards_for_public_space for public space %s: %s", public_space_id, str(e))
