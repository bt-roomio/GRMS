import time

from rest_framework.parsers import JSONParser
from rest_framework.views import APIView, Response

from main.models import Device
from main.utils.save_attributes import save_attributes
from main.utils.save_ts_kv import save_telemetry_kv
from shuttle.models import AttributeKv, Relation
from shuttle.serializers.attributes import AttributeKvParams, AttributesChangeFilterPath, AttributesChangeSerializer
from shuttle.swagger.attributes_change import swagger_attributes_change
from shuttle.utils.dynamic_model_query import dynamic_query
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
                defaults={"entity_type": "DEVICE", **fields, "last_update_ts": int(time.time())},
            )

        if params_data.get("scope") == AttributeKv.SERVER_SCOPE:
            return Response({}, 201)
        device_id = params_data.get("deviceId")
        send_rabbit_mq_attributes(device_id and device_id.id, available_fields)

        return Response({}, 201)


def send_rabbit_mq_attributes(params_device_id, available_fields):
    relation = Relation.objects.filter(to_id_id=params_device_id).first()
    device_id = relation and relation.from_id_id

    device = Device.objects.filter(pk=params_device_id).first()

    if device:
        attributes = dict((k, v[1]) for k, v in available_fields.items())
        message = {
            "targetDeviceUUID": str(device_id),
            "topic": "v1/gateway/attributes",
            "data": {"device": device.name, "data": attributes},
        }
        if device.additional_info and device.additional_info.get("gateway"):
            message["targetDeviceUUID"] = str(device.id)
            message["topic"] = "v1/devices/me/attributes"
            message["data"] = attributes

        send_to_rabbitmq(message)


class AttributesChangeRPCView(APIView):
    parser_classes = (JSONParser,)

    @swagger_attributes_change()
    def put(self, request, *args, **kwargs):
        path = AttributesChangeFilterPath.check(kwargs)
        model_name = path.get("entity_type") if path.get("entity_type") != "AllRoomType" else "Room"
        queryset = dynamic_query(model_name, ["main", "shuttle"], id=path.get("entity_id")).first()
        filters = {
            "Room": {"room": queryset},
            "RoomType": {"room__type": queryset},
            "AllRoomType": {"room__type__tenant": request.user.tenant},
        }
        devices = Device.objects.filter(**filters[path.get("entity_type")])
        serializer = AttributesChangeSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        changed_attrs = {"attributes": {}, "telemetry": {}}
        for entity in serializer.validated_data:
            if entity.get("type") == "ATTRIBUTES":
                changed_attrs["attributes"].update(
                    save_attributes(devices, entity.get("items", {}), entity.get("scope"))
                )
            elif entity.get("type") == "TELEMETRY":
                changed_attrs["telemetry"].update(save_telemetry_kv(devices, entity.get("items", {})))

        # ASK: don't send "SERVER_SCOPE" attributes ?
        # ASK: It's important response from mqtt ?

        merged_data = {}
        all_keys = set(changed_attrs["attributes"].keys()).union(set(changed_attrs["telemetry"].keys()))

        for key in all_keys:
            merged_data[key] = {}
            if key in changed_attrs["attributes"]:
                merged_data[key].update(changed_attrs["attributes"][key])
            if key in changed_attrs["telemetry"]:
                merged_data[key].update(changed_attrs["telemetry"][key])

        for device_id in merged_data:
            # send_rabbit_mq_attributes(device_id, merged_data[device_id])
            print(device_id, merged_data[device_id])

        return Response(changed_attrs)
