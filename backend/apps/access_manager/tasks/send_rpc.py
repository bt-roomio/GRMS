import logging
import time

from celery import shared_task
from rest_framework.generics import get_object_or_404

from access_manager.utilits.card_activate import activate_staff_card, activate_guest_card
from access_manager.utilits.card_deactivate import deactivate_staff_card, deactivate_guest_card
from access_manager.utilits.need_sync import need_sync
from access_manager.utilits.prepare_cards import prepare_cards
from core.rabbitmq.config import connect_to_rabbitmq, send_to_rabbitmq
from core.utils.str_to_dict import str_to_dict

from shuttle.models import Relation, RPCMessage

logger = logging.getLogger("main")


@shared_task(autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 60})
def send_rpc_request(device_id, cards, access, user=None, guest_id=None, staff_id=None, new_cards=None):
    from main.models import Device, Guest
    from access_manager.models import Staff

    device = Device.objects.get(id=device_id)
    guest = get_object_or_404(Guest, id=guest_id) if guest_id else None
    staff = get_object_or_404(Staff, id=staff_id) if staff_id else None
    group = staff.group if staff else None
    room_number = device.room.number if device.room else None
    public_spaces = list(
        device.device_public_spaces.select_related('public_space')
        .values_list('public_space__name', flat=True)
    )

    new_cards = new_cards or cards
    rpc_params = prepare_cards(cards, device, access, group=group)

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

    if not rpc_params:
        return {"success": True, "cards_empty": True, "message": "Cards are not provided ! "}

    channel = connect_to_rabbitmq()
    send_to_rabbitmq(channel, message)

    timeout_seconds = 10
    start_time = time.time()

    print(message, "\n\n")

    while time.time() - start_time < timeout_seconds:
        has_message = RPCMessage.objects.filter(id=request_id, received=True).first()
        is_success = str_to_dict(has_message.additional_info).get("success") if has_message else False
        if has_message and access == 0:
            if is_success:
                result = deactivate_staff_card(staff) if staff_id else deactivate_guest_card(new_cards, device)
                result.update({"room": room_number, "public_spaces": public_spaces})
                return result
            else:
                need_sync(new_cards, device, message, user=user)
                return {
                    "success": False,
                    "message": "Cards are not connected to device!",
                    "cards": cards,
                    "room": room_number,
                    "public_spaces": public_spaces,
                    "target_device": message.get("targetDeviceUUID")
                }
        elif has_message and is_success and access != 0:
            result = activate_staff_card(new_cards, staff, device) if staff_id else activate_guest_card(new_cards, device,
                                                                                                    guest)
            result.update({"room": room_number, "public_spaces": public_spaces})
            return result

        time.sleep(1)
    else:
        need_sync(new_cards, device, message, user=user)
        return {
            "success": False,
            "message": "Time out error!",
            "cards": cards,
            "room": room_number,
            "public_spaces": public_spaces,
            "target_device": message.get("targetDeviceUUID")
        }
