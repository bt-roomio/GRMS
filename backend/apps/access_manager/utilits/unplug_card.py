import logging

from access_manager.models import (
    GroupPublicSpace,
    GroupRoom,
    GuestCard,
    GuestPublicSpace,
    NeedSyncDevice,
    StaffCard,
)
from access_manager.utilits.task_trigger import card_public_space, card_room
from access_manager.tasks.send_rpc import send_rpc_request

from main.models import Device

logger = logging.getLogger(__name__)


def unplug(card):
    try:
        deactivate = True
        card_num = str(card.number)

        staff_cards = StaffCard.objects.filter(card=card, is_active=True).select_related("staff", "staff__group")
        guest_cards = GuestCard.objects.filter(card=card, is_active=True).select_related("guest", "guest__room")

        for staff_card in staff_cards:
            if staff_card.staff.group:
                group = staff_card.staff.group
                group_rooms = GroupRoom.objects.filter(group=group)
                for group_room in group_rooms:
                    card_room(group.id, group_room.room.id, "disconnect", card_num)

                group_public_spaces = GroupPublicSpace.objects.filter(group=group)
                for group_public_space in group_public_spaces:
                    card_public_space(group.id, group_public_space.public_space.id, "disconnect", card_num)

                staff_card.is_active = False
                staff_card.save()

        for guest_card in guest_cards:
            guest = guest_card.guest

            if guest.room:
                room_devices = Device.objects.filter(room=guest.room, is_active=True)
                for device in room_devices:
                    send_rpc_request.delay(str(device.id), [card_num], 0)
            guest_public_spaces = GuestPublicSpace.objects.filter(guest=guest).select_related("public_space")
            for guest_public_space in guest_public_spaces:
                public_space = guest_public_space.public_space
                public_space_devices = Device.objects.filter(
                    device_public_spaces__public_space=public_space,
                    is_active=True
                )
                for device in public_space_devices:
                    send_rpc_request.delay(str(device.id), [card_num], 0)

        need_sync_objs = NeedSyncDevice.objects.filter(card=card, need_sync=True).exists()

        if need_sync_objs:
            deactivate = False
        return deactivate

    except Exception as e:
        logger.error("Error disconnecting card %s: %s", {card.id}, {str(e)})
        return False