import uuid

from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from main.models import Device
from shuttle.models import Relation
from shuttle.swagger.rpc import RPCSwagger, RPCRequestSwagger


class JsonRpcView(APIView):
    @swagger_auto_schema(request_body=RPCRequestSwagger, responses={200: RPCSwagger})
    def post(self, request, device_id):
        device = get_object_or_404(Device, id=device_id)
        gateway_device = get_object_or_404(Relation, to_id_id=device_id)
        try:
            method = request.data["method"]
            params = request.data["params"]
            timeout = request.data["timeout"]
        except KeyError as err:
            return Response({"error": f"Missing {str(err)}"}, 400)

        methods = {"getValue": get_value(gateway_device, device, method, params, request, timeout)}

        if methods.get(method):
            return methods[method]

        return Response({"error": f"A method named '{method}' not found."}, 400)


def get_value(gateway_device, device, method, params, request, timeout):
    print("Getting value")
    message_id = uuid.uuid4()
    # send_to_rabbitmq_rpc(message_id, gateway_device, device, method, params)
    # Wait until response or changes in db, After sent rpc_message clear db.

    # 1. wait response in this function
    # 2. while every .5s check for db
    # instance = RPCMessage.objects.filter(id=message_id)
    # serializer = RPCMessageSerializer(instance)
    return Response({"device": "Device A", "id": message_id, "data": {"success": True}})
