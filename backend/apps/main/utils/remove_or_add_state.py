from main.models import Room


def remove_or_add(cond, room, state: Room.STATE):
    if cond and state not in room.state:
        room.state.append(state)
    elif not cond and state in room.state:
        room.state.remove(state)
    room.save()
