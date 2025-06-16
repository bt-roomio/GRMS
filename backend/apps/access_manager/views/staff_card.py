import logging
import time
from typing import cast, List

from access_manager.models import ALL_DAYS, WEEK_DAYS, Card, Group, GroupPublicSpace, GroupRoom, StaffCard, GuestCard
from access_manager.serializers.staff_card import StaffCardRequestData, StaffCardRequestSerializer
from access_manager.swagger.staff_card import staff_card_swagger

from rest_framework.response import Response
from rest_framework.views import APIView

from core.rabbitmq.config import connect_to_rabbitmq, send_to_rabbitmq
from core.utils.str_to_dict import str_to_dict
from main.models import Device
from shuttle.models import Relation, RPCMessage

logger = logging.getLogger("main")


class StaffCardView(APIView):
    @staff_card_swagger()
    def post(self, request):
        serializer = StaffCardRequestSerializer(data=request.data, context={"tenant_id": request.user.tenant_id})
        serializer.is_valid(raise_exception=True)

        try:
            validated_data = cast(StaffCardRequestData, serializer.validated_data)
            staff = validated_data["staff_id"]
            cards = validated_data["cards"]
            group = staff.group

            guest_cards = GuestCard.objects.filter(is_active=True, card__number__in=cards, guest__tenant_id=request.user.tenant_id)
            if guest_cards:
                return Response({"detail": "Card is connected to guest."}, 403)

            group_rooms_devices = GroupRoom.objects.filter(group=group, room__devices__is_active=True).values_list(
                "room__devices", flat=True
            )
            group_pub_spaces_devices = GroupPublicSpace.objects.filter(
                group=group, public_space__device__is_active=True
            ).values_list("public_space__device", flat=True)

            devices = Device.objects.filter(id__in=[*group_rooms_devices, *group_pub_spaces_devices])

            if not devices:
                return Response({"detail": "Not found device."}, 404)

            rpc_params = prepare_cards(cards, group, False)
            results = []
            for device in devices:
                result = prepare_mqtt_request(device, rpc_params, cards, staff)
                results.append(result)
            return Response(results)

        except Exception as e:
            return Response({"error": str(e)})


def get_indexes_of_day(group: Group):
    values = [day_value for (day_value, _) in WEEK_DAYS]
    indices = sorted([values.index(day) for day in group.week_days])
    return indices


def prepare_cards(cards: List[str], group: Group, connect: bool = True) -> List[dict]:
    rpc_params = []
    for card_number in cards:
        card_data = {
            "cardNumber": card_number,
            "access_group": str(group.group_type) if connect else "0",
            "start_time": str(group.start_time) if group.start_time else "00:00",
            "end_time": str(group.end_time) if group.end_time else "23:59",
            "weekdays": (
                ["1", "2", "3", "4", "5", "6", "7"] if ALL_DAYS in group.week_days else get_indexes_of_day(group)
            ),
            "slot_num": "1",
        }
        print(card_data)
        rpc_params.append(card_data)
    return rpc_params


def prepare_mqtt_request(device, rpc_params, cards, staff, deactiveate=False):
    from main.models import Device

    relation = Relation.objects.filter(to_id_id=device.id).order_by("updated_at").last()
    device_id = relation and relation.from_id.id
    gateway_or_none = Device.objects.gateway_or_none(device.id)  # pyright:ignore
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
    logger.debug(message)

    if not rpc_params:
        return {"success": False, "cards_empty": True, "message": "Cards doesn't exist. "}

    channel = connect_to_rabbitmq()
    send_to_rabbitmq(channel, message)

    timeout_seconds = 5
    start_time = time.time()

    while time.time() - start_time < timeout_seconds:
        has_message = RPCMessage.objects.filter(id=request_id, received=True).first()
        if deactiveate:
            if has_message and bool(str_to_dict(has_message.additional_info).get("success")):
                result = deactivate_staff_card(staff)
                return result
        elif has_message and bool(str_to_dict(has_message.additional_info).get("success")):
            result = activate_staff_card(cards, staff, device)
            return result

        time.sleep(1)

    return {
        "success": False,
        "device": device.name,
        "message": "Could not perform action with card, please try again !",
    }


def deactivate_staff_card(staff):
    try:
        StaffCard.objects.filter(staff=staff, is_active=True).update(is_active=False)
        return {"success": True, "error_guest_cards": 0, "message": "Card is deactivated."}
    except Exception:
        return {"success": False, "message": "Could not disconnect card, please try again !"}


def activate_staff_card(cards, staff, device):
    for card_number in cards:
        card, _ = Card.objects.get_or_create(number=card_number, tenant_id=staff.tenant_id,
                                             defaults={"is_active": True})

        if StaffCard.objects.filter(staff=staff, card=card, is_active=True).exists():
            continue

        StaffCard.objects.create(staff=staff, card=card, is_active=True)

    return {
        "success": True,
        "device": device.name,
        "message": "Successfully activated staff card.",
    }
