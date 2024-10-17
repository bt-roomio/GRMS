from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from main.models import Device
from shuttle.models import Relation
from shuttle.swagger.rpc import json_rpc_swagger


class JsonRpcView(APIView):
    @json_rpc_swagger()
    def post(self, request, device_id):
        device = get_object_or_404(Device, id=device_id)
        try:
            method = request.data["method"]
            params = request.data["params"]
            timeout = request.data["timeout"]
        except KeyError as err:
            return Response({"error": f"Missing {str(err)}"}, 400)

        return prepare_mqtt_request(device, method, params)


def prepare_mqtt_request(device, method, params):
    relation = Relation.objects.filter(to_id_id=device.id).first()
    device_id = relation and relation.from_id_id
    gateway_or_none = Device.objects.gateway_or_none(device_id)
    message = {
        "targetDeviceUUID": (gateway_or_none and str(gateway_or_none.id)) or str(device.id),
        "topic": "v1/gateway/rpc",
        "data": {"device": str(device.name), "data": {"id": 1, "method": method, "params": params}},
    }
    # send_to_rabbitmq(message)
    print(message)
    # channel = connect_to_rabbitmq()
    # message = json.dumps(message, indent=2).encode("utf-8")
    # channel.basic_publish(exchange="", routing_key="toGRMS", body=message)
    # channel.basic_consume(queue="toGRMS", on_message_callback=callback, auto_ack=True)
    # channel.start_consuming()

    # Wait until response or changes in db, After sent rpc_message clear db.
    # 1. wait response in this function
    # 2. while every .5s check for db
    # instance = RPCMessage.objects.filter(id=request_id)
    # serializer = RPCMessageSerializer(instance)
    return Response({"device": device.name, "id": 1, "data": {"success": True}})


def callback(ch, method, props, body):
    print(" Received body = %s ", body)
