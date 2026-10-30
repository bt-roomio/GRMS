import json

from services.mapping.resolver import TagMapper, Target, device_target
from services.serializers.device_tag_types import ATTRIBUTE, TAG_TYPES_KEY, TELEMETRY
from services.serializers.tag import RoomAttributeTagSerializer, RoomTelemetryTagSerializer, TagSerializer
from shuttle.models import AttributeKv, TsKvLatest


def _tag_type_entries(json_v, str_v) -> list:
    """``TAG_TYPES`` entries of an attribute row. A device may report the list as a JSON string."""
    if json_v is None and str_v:
        try:
            json_v = json.loads(str_v)
        except ValueError:
            return []
    return json_v if isinstance(json_v, list) else []


def _tag_types_by_tag(device_ids) -> dict[tuple, dict]:
    """Index the devices' ``TAG_TYPES`` entries by ``(device_id, section, sub_section, tag_name)``.
    Both the SERVER_SCOPE and CLIENT_SCOPE attributes are read; for the same tag the SERVER_SCOPE
    entry wins."""
    rows = AttributeKv.objects.filter(
        entity_id__in=device_ids,
        attribute_type__in=(AttributeKv.SERVER_SCOPE, AttributeKv.CLIENT_SCOPE),
        attribute_key=TAG_TYPES_KEY,
    ).values_list("entity_id", "attribute_type", "json_v", "str_v")
    # CLIENT_SCOPE first, so SERVER_SCOPE entries overwrite them in the index.
    rows = sorted(rows, key=lambda row: row[1] == AttributeKv.SERVER_SCOPE)
    index = {}
    for device_id, _, json_v, str_v in rows:
        for entry in _tag_type_entries(json_v, str_v):
            if not isinstance(entry, dict):
                continue
            parts = (entry.get("tag_section"), entry.get("tag_sub_section"), entry.get("tag_name"))
            # A device-reported entry is unvalidated; skip one whose key parts are not hashable strings.
            if all(part is None or isinstance(part, str) for part in parts):
                index[(device_id, *parts)] = entry
    return index


def _tag_type_fields(entry) -> dict:
    """``tag_type`` and ``tag_ranges`` of a ``TAG_TYPES`` entry; both ``null`` when there is no entry
    or it has the wrong data types (``tag_type`` not a non-empty string or ``tag_ranges`` not a list)."""
    entry = entry or {}
    tag_type, tag_ranges = entry.get("tag_type"), entry.get("tag_ranges")
    valid = isinstance(tag_type, str) and bool(tag_type) and isinstance(tag_ranges, list)
    return {"tag_type": tag_type if valid else None, "tag_ranges": tag_ranges if valid else None}


def _with_tag_types(rows, tags, lookup, mapper, room):
    """Add ``tag_type`` and ``tag_ranges`` from the tag's entry in its device's ``TAG_TYPES``, then
    convert the tag to the integrator's form."""
    for row, tag in zip(rows, tags, strict=True):
        tag.update(_tag_type_fields(lookup(row)))
        mapper.tag_to_external(tag, Target(row["entity_id"], room.type_id))
    return tags


def room_tags(room, tenant, mapper: TagMapper | None = None) -> list[dict]:
    """The room's CLIENT_SCOPE attributes and latest telemetry as one tag list, each part ordered by
    key. Shared by the REST view and the WebSocket consumer so both return the same shape.
    ``mapper`` converts values and ranges to the integration's form; none leaves GRMS values."""
    mapper = mapper or TagMapper()
    # A device-reported CLIENT_SCOPE TAG_TYPES is configuration, not a tag.
    attributes = list(
        AttributeKv.objects.get_attributes_by_room(
            room, AttributeKv.CLIENT_SCOPE, sort_by=("attribute_key", "id")
        ).exclude(attribute_key=TAG_TYPES_KEY)
    )
    telemetry = list(TsKvLatest.objects.get_ts_kv_latest_by_room(room, tenant, sort_by=("key__key", "id")))
    tag_types = _tag_types_by_tag({row["entity_id"] for row in [*attributes, *telemetry]})
    return [
        *_with_tag_types(
            attributes,
            RoomAttributeTagSerializer(attributes, many=True).data,
            lambda row: tag_types.get((row["entity_id"], ATTRIBUTE, AttributeKv.CLIENT_SCOPE, row["attribute_key"])),
            mapper,
            room,
        ),
        *_with_tag_types(
            telemetry,
            RoomTelemetryTagSerializer(telemetry, many=True).data,
            lambda row: tag_types.get((row["entity_id"], TELEMETRY, None, row["key__key"])),
            mapper,
            room,
        ),
    ]


def paginated_room_tags(room, tenant, page, size, mapper: TagMapper | None = None) -> dict:
    """One page of ``room_tags`` as ``{count, results}``."""
    tags = room_tags(room, tenant, mapper)
    offset = (page - 1) * size
    return {"count": len(tags), "results": tags[offset : offset + size]}


def tag_type_fields(tag) -> dict:
    """``tag_type`` and ``tag_ranges`` of a single AttributeKv/TsKvLatest tag from its device's
    ``TAG_TYPES``, in GRMS form."""
    if isinstance(tag, AttributeKv):
        key = (tag.entity_id, ATTRIBUTE, tag.attribute_type, tag.attribute_key)
    else:
        key = (tag.entity_id, TELEMETRY, None, tag.key.key)
    return _tag_type_fields(_tag_types_by_tag({tag.entity_id}).get(key))


def tag_with_type(tag, mapper: TagMapper | None = None) -> dict:
    """A single AttributeKv/TsKvLatest tag with ``tag_type`` and ``tag_ranges`` from its device's
    ``TAG_TYPES``, so the tag detail matches the room tag list. ``mapper`` converts it to the
    integration's form; the tag's ``entity__room`` should be selected with it."""
    data = {**TagSerializer(tag).data, **tag_type_fields(tag)}
    return (mapper or TagMapper()).tag_to_external(data, device_target(tag.entity))
