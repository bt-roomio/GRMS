from access_manager.utilits.get_device_cards import get_device_cards
from access_manager.utilits.prepare_cards import prepare_cards

from rest_framework.generics import get_object_or_404

from shuttle.models import Relation, RPCMessage


def prepare_rpc_request(device_id, cards, access, guest_id=None, staff_id=None):
    from access_manager.models import Staff

    from main.models import Device, Guest

    device = Device.objects.get(id=device_id)
    cards_of_device = get_device_cards(device.id, cards, access)
    guest = get_object_or_404(Guest, id=guest_id) if guest_id else None
    staff = get_object_or_404(Staff, id=staff_id) if staff_id else None
    group = staff.group if staff else None
    room_number = device.room.number if device.room else None
    public_spaces = list(
        device.device_public_spaces.select_related('public_space')
        .values_list('public_space__name', flat=True)
    )

    rpc_params = prepare_cards(cards_of_device, device, access, group=group)

    relation = Relation.objects.filter(to_id_id=device.id).order_by("updated_at").last()
    device_id = relation and relation.from_id.id
    gateway_or_none = Device.objects.gateway_or_none(device.id)
    rpc_message = RPCMessage.objects.create(additional_info={})
    request_id = rpc_message.id

    message = {
        "targetDeviceUUID": (gateway_or_none and str(gateway_or_none.id)) or str(device_id),
        "topic": "v1/gateway/rpc",
        "data": {
            "device": str(device.name),
            "data": {"id": request_id, "method": "writeRFID", "params": rpc_params, "timeout": 10000},
        },
    }

    fail_response = {
        "success": False, "message": "Cards are not connected to device!", "cards": cards,
        "device": str(device.name), "room": room_number, "public_spaces": public_spaces,
        "target_device": message.get("targetDeviceUUID")
    }

    result = {"message": message, "request_id": request_id, "room_number": room_number,
              "public_spaces": public_spaces,
              "staff": staff, "guest": guest, "device": device, "fail_response": fail_response}

    return result
