import time

from rest_framework.parsers import JSONParser
from rest_framework.views import APIView, Response

from main.models import Device
from shuttle.models import AttributeKv, Relation
from shuttle.serializers.attributes import AttributeKvParams
from shuttle.utils.find_compatible_field import find_compatible_field
from shuttle.utils.send_to_rabbitmq import send_to_rabbitmq


class AttributeListView(APIView):
    parser_classes = (JSONParser,)

    def post(self, request, *args, **kwargs):
        params = AttributeKvParams(data=kwargs)
        params.is_valid(raise_exception=True)
        params_data = params.validated_data
        available_fields = find_compatible_field(request.data)

        for key, item in available_fields.items():
            fields = {"bool_v": None, "str_v": None, "long_v": None, "dbl_v": None, "json_v": None}
            field = item[0]
            value = item[1]
            fields[field] = value
            attribute_kv, _ = AttributeKv.objects.update_or_create(
                entity=params_data.get("deviceId"),
                attribute_type=params_data.get("scope"),
                attribute_key=key,
                defaults={"entity_type": "DEVICE", **fields, "last_update_ts": time.time()},
            )

        relation = Relation.objects.filter(to_id=params_data.get("deviceId")).first()
        device_id = relation and relation.from_id

        device = Device.objects.filter(pk=params_data.get("deviceId").id).first()
        if device:
            attributes = dict((k, v[1]) for k, v in available_fields.items())
            message = {
                "targetDeviceUUID": str(device_id),
                "topic": "v1/gateway/attributes",
                "data": {"device": str(device_id and device_id.id or device.id), "data": attributes},
            }
            if device.additional_info and device.additional_info.get("gateway"):
                message["topic"] = "v1/devices/me/attributes/"
                message["data"] = attributes

            send_to_rabbitmq(message)

        return Response({}, 201)
