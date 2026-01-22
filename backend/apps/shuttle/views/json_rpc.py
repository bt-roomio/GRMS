import logging
import os
import time

from django.conf import settings

from rest_framework.response import Response
from rest_framework.views import APIView

from core.rabbitmq.config import connect_to_rabbitmq, send_to_rabbitmq
from core.utils.helpers import b_encode, compress_data, read_binary
from core.utils.permission import check_perms
from main.models import Device
from shuttle.models import ControllerFile, Relation, RPCMessage
from shuttle.swagger.rpc import json_rpc_swagger
from shuttle.utils.parse_json import parse_json
from shuttle.utils.permissions import WhiteListOrIsAuthenticated

logger = logging.getLogger("main")


class JsonRPCView(APIView):
    permission_classes = (WhiteListOrIsAuthenticated,)

    @json_rpc_swagger()
    @check_perms(["shuttle.send_jsonrpc"])
    def post(self, request, **kwargs):
        kwargs = self.handle_params(**kwargs)
        device = Device.objects.filter(**kwargs).first()
        if not device:
            return Response({"detail": "Not found device."}, 404)

        try:
            method = request.data["method"]
            params = request.data["params"]
            timeout = request.data["timeout"]
        except KeyError as err:
            return Response({"error": f"Missing {str(err)}"}, 400)

        result = prepare_mqtt_request(device, method, params, timeout / 1000)

        return Response(result)

    def handle_params(self, **kwargs):
        result = {}
        if kwargs.get("hotel_id") and kwargs.get("room_number"):
            result["tenant__additional_info__integration_settings__hoteza__hotel_id"] = kwargs.get("hotel_id")
            result["room__number"] = kwargs.get("room_number")
            return result
        elif kwargs.get("device_id"):
            result["id"] = kwargs.get("device_id")
            return result
        elif kwargs.get("tenant_id") and kwargs.get("room_number"):
            result["tenant_id"] = kwargs.get("tenant_id")
            result["room__number"] = kwargs.get("room_number")
            return result
        return result


def prepare_mqtt_request(device, method, params, timeout):
    relation = Relation.objects.filter(to_id_id=device.id).order_by("updated_at").last()
    device_id = relation and relation.from_id.id
    gateway_or_none = Device.objects.gateway_or_none(device.id)  # pyright: ignore
    rpc_message = RPCMessage.objects.create(additional_info={})
    request_id = rpc_message.id
    message = {
        "targetDeviceUUID": (gateway_or_none and str(gateway_or_none.id)) or str(device_id),
        "topic": "v1/gateway/rpc",
        "data": {"device": str(device.name), "data": {"id": request_id, "method": method, "params": params}},
    }

    for param in params:
        if method == "uploadConfiguration" and param.get("file", {}).get("id"):
            file_id = param.get("file").get("id")
            file = ControllerFile.objects.filter(id=file_id).first()
            if not file:
                return {"error": "Not found file."}
            file_name = file.content.path.split("/")[-1][11:]
            param["file"]["name"] = file_name
            param["file"]["content"] = str(
                b_encode(compress_data(read_binary(os.path.join(settings.MEDIA_ROOT, str(file.content)))))
            )

    logger.debug(message)
    channel = connect_to_rabbitmq()
    send_to_rabbitmq(channel, message)
    start_time = 0

    while start_time < timeout:
        has_message = RPCMessage.objects.filter(id=request_id, received=True)
        has_message = has_message.first()
        if has_message:
            payload = has_message.additional_info
            return parse_json(payload)
        time.sleep(0.3)
        start_time += 1

    return {"device": device.name, "data": {"success": False, "msg": "Timeout error"}}
