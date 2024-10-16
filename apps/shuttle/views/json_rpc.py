from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from main.models import Device
from shuttle.models import Relation
from shuttle.swagger.rpc import json_rpc_swagger
from shuttle.utils.send_to_rabbitmq import send_to_rabbitmq


class JsonRpcView(APIView):
    @json_rpc_swagger()
    def post(self, request, device_id):
        device = get_object_or_404(Device, id=device_id)
        gateway_device = get_object_or_404(Relation, to_id_id=device_id)
        try:
            method = request.data["method"]
            params = request.data["params"]
            timeout = request.data["timeout"]
        except KeyError as err:
            return Response({"error": f"Missing {str(err)}"}, 400)

        return prepare_mqtt_request(gateway_device, device, method, params, request, timeout)


def prepare_mqtt_request(gateway_device, device, method, params, request, timeout):
    print("Getting value")
    message = {
        "targetDeviceUUID": str(device.id),
        "topic": "v1/gateway/rpc",
        "data": {"device": str(device.name), "data": {"id": 1, "method": method, "params": params}},
    }
    send_to_rabbitmq(message)

    # Wait until response or changes in db, After sent rpc_message clear db.
    # 1. wait response in this function
    # 2. while every .5s check for db
    # instance = RPCMessage.objects.filter(id=request_id)
    # serializer = RPCMessageSerializer(instance)
    return Response({"device": device.name, "id": 1, "data": {"success": True}})
