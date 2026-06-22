from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.get_time import get_mil_sec
from main.models import Room
from services.serializers.room import RoomSerializer
from services.serializers.tag import TagSerializer, TagUpdateSerializer
from services.swagger.tags import tag_detail_get_swagger, tag_detail_put_swagger, tags_by_room_get_swagger
from services.utils.permissions import DoorLockPermission
from shuttle.models import AttributeKv, TsKvLatest
from shuttle.serializers.attributes import RoomAttributeSerializer
from shuttle.serializers.ts_kv_latest import RoomTsKvLatestSerializer
from shuttle.utils.find_compatible_field import find_compatible_field
from shuttle.views.json_rpc import prepare_mqtt_request

VALUE_COLUMNS = ("bool_v", "str_v", "long_v", "dbl_v", "json_v")


class TagsByRoomListView(APIView):
    permission_classes = (DoorLockPermission,)
    parser_classes = (JSONParser,)

    @tags_by_room_get_swagger()
    def get(self, request, room_id):
        room = get_object_or_404(Room.objects.by_tenant(request.tenant), pk=room_id)
        attributes = AttributeKv.objects.get_attributes_by_room(room, AttributeKv.CLIENT_SCOPE)
        telemetry = TsKvLatest.objects.get_ts_kv_latest_by_room(room, request.tenant)
        print(attributes.values())
        return Response(
            {
                "room": RoomSerializer(room).data,
                "attributes": RoomAttributeSerializer(attributes, many=True).data,
                "telemetry": RoomTsKvLatestSerializer(telemetry, many=True).data,
            }
        )


class TagDetailView(APIView):
    permission_classes = (DoorLockPermission,)
    parser_classes = (JSONParser,)

    def get_tag(self, request, tag_id):
        """A tag id may reference an AttributeKv (attribute) or a TsKvLatest (telemetry)."""
        tag = AttributeKv.objects.select_related("entity").filter(entity__tenant=request.tenant, pk=tag_id).first()
        if tag is None:
            tag = (
                TsKvLatest.objects.select_related("entity", "key")
                .filter(entity__tenant=request.tenant, pk=tag_id)
                .first()
            )
        if tag is None:
            raise NotFound("Tag not found.")
        return tag

    @tag_detail_get_swagger()
    def get(self, request, tag_id):
        tag = self.get_tag(request, tag_id)
        return Response(TagSerializer(tag).data)

    @tag_detail_put_swagger()
    def put(self, request, tag_id):
        tag = self.get_tag(request, tag_id)

        serializer = TagUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        value = serializer.validated_data["value"]

        is_attribute = isinstance(tag, AttributeKv)
        key = tag.attribute_key if is_attribute else tag.key.key

        mapping = find_compatible_field({key: value})
        if key not in mapping:
            raise ValidationError({"value": f"Unsupported value type: {type(value).__name__}."})

        field, val = mapping[key]
        for column in VALUE_COLUMNS:
            setattr(tag, column, None)
        setattr(tag, field, val)
        if not is_attribute:
            tag.ts = get_mil_sec()  # TsKvLatest.save() does not refresh ts; AttributeKv.save() does
        tag.save()

        method = "setAttribute" if is_attribute else "setTelemetry"
        rpc = prepare_mqtt_request(tag.entity, method, {key: value}, 5)
        return Response({"tag": TagSerializer(tag).data, "rpc": rpc})
