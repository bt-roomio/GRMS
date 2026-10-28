from django.db.models import F

from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.serializers.pagination import PaginationSerializer
from core.utils.get_time import get_mil_sec
from main.models import Room
from services.mapping.engine import SKIP, MappingError
from services.mapping.resolver import TagMapper, device_target
from services.serializers.room import RoomSerializer
from services.serializers.tag import TagUpdateSerializer
from services.swagger.tags import tag_detail_get_swagger, tag_detail_put_swagger, tags_by_room_get_swagger
from services.utils.permissions import DoorLockPermission
from services.utils.room_tags import paginated_room_tags, tag_type_fields, tag_with_type
from shuttle.models import AttributeKv, TsKvLatest
from shuttle.utils.find_compatible_field import find_compatible_field
from shuttle.views.json_rpc import prepare_mqtt_request

VALUE_COLUMNS = ("bool_v", "str_v", "long_v", "dbl_v", "json_v")


def _rpc_succeeded(rpc) -> bool:
    """Whether a ``prepare_mqtt_request`` result means the device accepted the change.
    A real device response carries a top-level ``success`` flag (see access_manager
    send_rpc), while the timeout sentinel nests ``success: False`` under ``data``."""
    if not isinstance(rpc, dict) or "error" in rpc:
        return False
    data = rpc.get("data")
    if isinstance(data, dict) and "success" in data:
        return bool(data["success"])
    return bool(rpc.get("success"))


class TagsByRoomListView(APIView):
    permission_classes = (DoorLockPermission,)
    parser_classes = (JSONParser,)

    @tags_by_room_get_swagger()
    def get(self, request, room_id):
        rooms = Room.objects.by_tenant(request.tenant).annotate(type_name=F("type__title"))
        room = get_object_or_404(rooms, pk=room_id)
        params = PaginationSerializer.parse(request.query_params)
        tags = paginated_room_tags(room, request.tenant, params.page, params.size, TagMapper(request.integration))
        return Response({"room": RoomSerializer(room).data, **tags})


class TagDetailView(APIView):
    permission_classes = (DoorLockPermission,)
    parser_classes = (JSONParser,)

    def get_tag(self, request, tag_id):
        """A tag id may reference an AttributeKv (attribute) or a TsKvLatest (telemetry)."""
        tag = (
            AttributeKv.objects.select_related("entity__room").filter(entity__tenant=request.tenant, pk=tag_id).first()
        )
        if tag is None:
            tag = (
                TsKvLatest.objects.select_related("entity__room", "key")
                .filter(entity__tenant=request.tenant, pk=tag_id)
                .first()
            )
        if tag is None:
            raise NotFound("Tag not found.")
        return tag

    @tag_detail_get_swagger()
    def get(self, request, tag_id):
        tag = self.get_tag(request, tag_id)
        return Response(tag_with_type(tag, TagMapper(request.integration)))

    @tag_detail_put_swagger()
    def put(self, request, tag_id):
        tag = self.get_tag(request, tag_id)

        serializer = TagUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        mapper = TagMapper(request.integration)

        # The integrator sends values in its own form; write the GRMS value.
        fields = tag_type_fields(tag)
        try:
            value = mapper.value_to_grms(
                serializer.validated_data["value"], fields["tag_type"], fields["tag_ranges"], device_target(tag.entity)
            )
        except MappingError as exc:
            return Response({"value": [str(exc)], "code": exc.code}, status=400)
        if value is SKIP:
            # The rule drops invalid values: nothing is sent to the device.
            return Response({"tag": tag_with_type(tag, mapper), "rpc": None, "skipped": True})

        is_attribute = isinstance(tag, AttributeKv)
        key = tag.attribute_key if is_attribute else tag.key.key

        mapping = find_compatible_field({key: value})
        if key not in mapping:
            raise ValidationError({"value": f"Unsupported value type: {type(value).__name__}."})

        # 1. Push to the device first; persist only if it accepts the change.
        method = "setAttribute" if is_attribute else "setTelemetry"
        rpc = prepare_mqtt_request(tag.entity, method, {key: value}, 5)

        if not _rpc_succeeded(rpc):
            # Device rejected or did not respond — keep the stored value unchanged.
            return Response({"tag": tag_with_type(tag, mapper), "rpc": rpc}, status=502)

        # 2. Device accepted — persist the new value.
        field, val = mapping[key]
        for column in VALUE_COLUMNS:
            setattr(tag, column, None)
        setattr(tag, field, val)
        if not is_attribute:
            tag.ts = get_mil_sec()  # TsKvLatest.save() does not refresh ts; AttributeKv.save() does
        tag.save()

        return Response({"tag": tag_with_type(tag, mapper), "rpc": rpc})
