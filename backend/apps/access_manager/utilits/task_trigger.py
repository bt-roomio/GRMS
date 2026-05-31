from access_manager.tasks.public_space_card import manage_cards_for_public_space_task
from access_manager.tasks.room_card import manage_cards_for_room_task


def card_room(group_id, room_id, action, card_num=None):
    try:
        result = manage_cards_for_room_task.delay(str(group_id), str(room_id), action, card_num=card_num)
        return f"Connect/Disconect task result: {result}"
    except Exception as e:
        return f"Error connecting cards to room: {str(e)}"


def card_public_space(group_id, public_space_id, action, card_num=None):
    try:
        result = manage_cards_for_public_space_task.delay(
            str(group_id), str(public_space_id), action, card_num=card_num
        )
        return f"Connect/Disconect public space task result: {result}"
    except Exception as e:
        return f"Error connecting cards to public space: {str(e)}"
