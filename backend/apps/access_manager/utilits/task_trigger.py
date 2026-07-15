import logging

from access_manager.tasks.public_space_card import manage_cards_for_public_space_task
from access_manager.tasks.room_card import manage_cards_for_room_task

logger = logging.getLogger(__name__)


def card_room(group_id, room_id, action, card_num=None):
    try:
        result = manage_cards_for_room_task.delay(str(group_id), str(room_id), action, card_num=card_num)
        logger.info("Queued room card task %s: action=%s room=%s", result.id, action, room_id)
        return f"Connect/Disconect task result: {result}"
    except Exception as e:
        logger.exception("Error triggering room card task for room=%s", room_id)
        return f"Error connecting cards to room: {str(e)}"


def card_public_space(group_id, public_space_id, action, card_num=None):
    try:
        result = manage_cards_for_public_space_task.delay(
            str(group_id), str(public_space_id), action, card_num=card_num
        )
        logger.info("Queued public space card task %s: action=%s public_space=%s", result.id, action, public_space_id)
        return f"Connect/Disconect public space task result: {result}"
    except Exception as e:
        logger.exception("Error triggering public space card task for public_space=%s", public_space_id)
        return f"Error connecting cards to public space: {str(e)}"
