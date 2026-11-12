from django.core.cache import cache
from django.db.models import F

from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.serializers.pagination import PaginationSerializer
from main.models import Room
from services.mapping.engine import SKIP, MappingError
from services.mapping.resolver import TagMapper, device_target
from services.serializers.room import RoomSerializer
from services.serializers.tag import TagUpdateSerializer
from services.swagger.tags import tag_detail_get_swagger, tag_detail_put_swagger, tags_by_room_get_swagger
from services.utils.composite_tags import execute_writes, plan_writes
from services.utils.permissions import DoorLockPermission
from services.utils.room_tags import ResolvedTag, paginated_room_tags, resolve_tag, tag_type_fields, tag_with_type
from services.utils.tag_write import storable, tag_key, write_tag_value

# The longest a composite write chain may hold its tag: several RPCs, each waiting for its device.
COMPOSITE_WRITE_LOCK_TTL = 120


def _mapping_error(exc: MappingError) -> Response:
    return Response({"value": [str(exc)], "code": exc.code, "field": exc.field}, status=400)


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

    @tag_detail_get_swagger()
    def get(self, request, tag_id):
        return Response(resolve_tag(request.tenant, tag_id, TagMapper(request.integration)).data)

    @tag_detail_put_swagger()
    def put(self, request, tag_id):
        serializer = TagUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        value = serializer.validated_data["value"]
        mapper = TagMapper(request.integration)
        resolved = resolve_tag(request.tenant, tag_id, mapper)
        if resolved.binding is not None:
            return self.put_composite(request, resolved, value, mapper)

        tag = resolved.model
        assert tag is not None  # a tag no composite rule computes is an attribute or telemetry
        key = tag_key(tag)
        # The integrator sends values in its own form; write the GRMS value.
        tag_ranges = tag_type_fields(tag)["tag_ranges"]
        try:
            value = mapper.value_to_grms(value, key, tag_ranges, device_target(tag.entity))
        except MappingError as exc:
            return _mapping_error(exc)
        if value is SKIP:
            # The rule drops invalid values: nothing is sent to the device.
            return Response({"tag": resolved.data, "rpc": None, "skipped": True})
        if not storable(tag, value):
            raise ValidationError({"value": f"Unsupported value type: {type(value).__name__}."})

        # The device first; the value is stored only if it accepts the change.
        result = write_tag_value(tag, value)
        return Response({"tag": tag_with_type(tag, mapper), "rpc": result.rpc}, status=200 if result.ok else 502)

    @staticmethod
    def put_composite(request, resolved: ResolvedTag, value, mapper):
        """One integrator value as the ordered writes of its composite action. Every write is
        checked before the first RPC; a failed required write stops the rest and answers 502 with
        the status of each write. One write of a composite tag runs at a time: another one meanwhile
        answers 409, so two chains never interleave their writes."""
        assert resolved.index is not None and resolved.binding is not None
        try:
            writes = plan_writes(resolved.binding, resolved.index, value)
        except MappingError as exc:
            return _mapping_error(exc)
        if writes is SKIP:
            return Response({"tag": resolved.data, "actions": [], "skipped": True})

        lock = f"services:composite-write:{resolved.data['id']}"
        if not cache.add(lock, 1, timeout=COMPOSITE_WRITE_LOCK_TTL):
            body = {"detail": "Another write of this tag is in progress.", "code": "busy"}
            return Response(body, status=409)
        try:
            success, actions = execute_writes(writes)
        except MappingError as exc:
            return _mapping_error(exc)
        finally:
            cache.delete(lock)
        tag = resolve_tag(request.tenant, resolved.data["id"], mapper).data
        partial = not success and any(action["status"] == "ok" for action in actions)
        body = {"tag": tag, "actions": actions, "success": success, "partial": partial}
        return Response(body, status=200 if success else 502)
