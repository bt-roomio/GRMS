import json
import time

from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from main.models import Device
from shuttle.models import Relation, RPCMessage
from shuttle.swagger.rpc import json_rpc_swagger
from shuttle.utils.send_to_rabbitmq import connect_to_rabbitmq


class JsonRPCView(APIView):
    @json_rpc_swagger()
    def post(self, request, device_id):
        device = get_object_or_404(Device, id=device_id)
        try:
            method = request.data["method"]
            params = request.data["params"]
            timeout = request.data["timeout"]
        except KeyError as err:
            return Response({"error": f"Missing {str(err)}"}, 400)

        result = prepare_mqtt_request(device, method, params, timeout / 1000)

        return Response(result)


def prepare_mqtt_request(device, method, params, timeout):
    relation = Relation.objects.filter(to_id_id=device.id).first()
    device_id = relation and relation.from_id_id
    gateway_or_none = Device.objects.gateway_or_none(device_id)
    rpc_message = RPCMessage.objects.create(additional_info={})
    request_id = rpc_message.id
    message = {
        "targetDeviceUUID": (gateway_or_none and str(gateway_or_none.id)) or str(device.id),
        "topic": "v1/gateway/rpc",
        "data": {"device": str(device.name), "data": {"id": request_id, "method": method, "params": params}},
    }

    channel = connect_to_rabbitmq()
    message = json.dumps(message, indent=2).encode("utf-8")
    channel.basic_publish(exchange="", routing_key="fromGRMS", body=message)

    start_time = 0
    while start_time < timeout:
        has_message = RPCMessage.objects.filter(id=request_id, received=True)
        if has_message:
            return has_message.first().additional_info
        time.sleep(1)
        start_time += 1

    return {"device": device.name, "data": {"success": False, "msg": "Timeout error"}}
