from core.utils.helpers import safely_remove
from main.models import Room


def make_checkedin(room: Room):
    room.state = safely_remove(room.state, Room.Available)
    room.state.append(Room.CheckedIn)
    room.save(update_fields=["state"])


def make_checkedout(room: Room):
    room.state = safely_remove(room.state, Room.CheckedIn)
    room.state.append(Room.Available)
    room.save(update_fields=["state"])
