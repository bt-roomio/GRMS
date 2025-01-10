from rest_framework.parsers import JSONParser
from rest_framework.views import APIView, Response

from core.rabbitmq.config import connect_to_rabbitmq, send_to_rabbitmq
from main.models import Device
from main.utils.save_attributes import save_attributes
from shuttle.consumers.aggregations.latest_telemetry import get_ts_kv_dict
from shuttle.models import AttributeKv, Relation, TsKvDictionary, TsKvLatest
from shuttle.serializers.attributes import AttributeKvPath, AttributesChangeFilterPath, AttributesChangeSerializer
from shuttle.serializers.tag import TagFilterParams, TagFilterPath
from shuttle.swagger.attributes_change import swagger_attributes_change
from shuttle.swagger.tag import tag_swagger
from shuttle.utils.dynamic_model_query import dynamic_query
from shuttle.utils.find_compatible_field import find_compatible_field
from shuttle.utils.get_non_null_field import get_non_null_field
from shuttle.views.json_rpc import prepare_mqtt_request


class AttributeListView(APIView):
    parser_classes = (JSONParser,)

    @tag_swagger()
    def get(self, request, *args, **kwargs):
        path = TagFilterPath.check(kwargs)
        params = TagFilterParams.check(request.GET)
        if path.get("scope") != "LATEST_TELEMETRY":
            result = {"data": {}, "latestValues": {}}
            queryset = AttributeKv.objects.filter(
                entity_id=path.get("device_id"),
                attribute_type=path.get("scope"),
                attribute_key__in=params.get("tags"),
                entity__tenant_id=request.user.tenant_id,
            )
            for attribute in queryset:
                _, value = get_non_null_field(attribute)
                ts = attribute.last_update_ts
                result["data"][attribute.attribute_key] = [[ts, value]]
                result["latestValues"][attribute.attribute_key] = ts
        else:
            result = {"data": {}, "latestValues": {}}
            keys = TsKvDictionary.objects.get_key_ids(params.get("tags"))
            queryset = TsKvLatest.objects.filter(
                key__in=keys,
                entity_id=path.get("device_id"),
                entity__tenant_id=request.user.tenant_id,
            )
            for d in queryset:
                ts_kv_dict = get_ts_kv_dict(d.key)
                _, value = get_non_null_field(d)
                result["data"][ts_kv_dict.key] = [[d.ts, value]]
                result["latestValues"][ts_kv_dict.key] = d.ts

        return Response(result)

    def post(self, request, *args, **kwargs):
        path = AttributeKvPath(data=kwargs)
        path.is_valid(raise_exception=True)
        path_data = path.validated_data

        available_fields = find_compatible_field(request.data)

        save_attributes([path_data.get("device_id").id], available_fields, path_data.get("scope"))

        if path_data.get("scope") == AttributeKv.SERVER_SCOPE:
            return Response({}, 201)

        device_id = path_data.get("device_id")
        send_rabbit_mq_attributes(device_id and device_id.id, available_fields)

        return Response({}, 201)


def send_rabbit_mq_attributes(path_device_id, available_fields):
    relation = Relation.objects.filter(to_id_id=path_device_id).first()
    device_id = relation and relation.from_id_id

    device = Device.objects.filter(pk=path_device_id).first()

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

        channel = connect_to_rabbitmq()
        send_to_rabbitmq(channel, message)


class AttributesChangeRPCView(APIView):
    parser_classes = (JSONParser,)

    @swagger_attributes_change()
    def post(self, request, *args, **kwargs):
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
            entity_type = entity.get("type")
            entity_scope = entity.get("scope")
            entity_items = entity.get("items")
            if entity_type == "ATTRIBUTES" and entity_scope in (AttributeKv.SHARED_SCOPE, AttributeKv.SERVER_SCOPE):
                devices = devices.values_list("id", flat=True)
                available_fields = find_compatible_field(entity_items)
                changed_attrs["attributes"].update(save_attributes(devices, available_fields, entity_scope))
                if entity_scope == AttributeKv.SERVER_SCOPE:
                    continue
                for device_id in devices:
                    send_rabbit_mq_attributes(device_id, available_fields)
            elif entity_type == "TELEMETRY" or (
                entity_type == "ATTRIBUTES" and entity_scope == AttributeKv.CLIENT_SCOPE
            ):
                entity_type_method = {
                    "TELEMETRY": "setTelemetry",
                    "ATTRIBUTES": "setAttribute",
                }
                for device in devices:
                    changed_attrs["telemetry"].update(
                        {str(device.id): prepare_mqtt_request(device, entity_type_method[entity_type], entity_items, 5)}
                    )

        return Response(changed_attrs)
