import json

from services.serializers.device_tag_types import ATTRIBUTE, TAG_TYPES_KEY, TELEMETRY
from services.serializers.tag import RoomAttributeTagSerializer, RoomTelemetryTagSerializer
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


def _with_tag_types(rows, tags, lookup):
    """Add ``tag_type`` and ``tag_ranges`` from the tag's entry in its device's ``TAG_TYPES``;
    both are ``null`` when the tag has no entry or the entry has the wrong data types
    (``tag_type`` not a non-empty string or ``tag_ranges`` not a list)."""
    for row, tag in zip(rows, tags, strict=True):
        entry = lookup(row) or {}
        tag_type, tag_ranges = entry.get("tag_type"), entry.get("tag_ranges")
        valid = isinstance(tag_type, str) and bool(tag_type) and isinstance(tag_ranges, list)
        tag["tag_type"] = tag_type if valid else None
        tag["tag_ranges"] = tag_ranges if valid else None
    return tags


def room_tags(room, tenant) -> list[dict]:
    """The room's CLIENT_SCOPE attributes and latest telemetry as one tag list. Shared by the REST
    view and the WebSocket consumer so both return the same shape."""
    # A device-reported CLIENT_SCOPE TAG_TYPES is configuration, not a tag.
    attributes = list(
        AttributeKv.objects.get_attributes_by_room(room, AttributeKv.CLIENT_SCOPE).exclude(attribute_key=TAG_TYPES_KEY)
    )
    telemetry = list(TsKvLatest.objects.get_ts_kv_latest_by_room(room, tenant))
    tag_types = _tag_types_by_tag({row["entity_id"] for row in [*attributes, *telemetry]})
    return [
        *_with_tag_types(
            attributes,
            RoomAttributeTagSerializer(attributes, many=True).data,
            lambda row: tag_types.get((row["entity_id"], ATTRIBUTE, AttributeKv.CLIENT_SCOPE, row["attribute_key"])),
        ),
        *_with_tag_types(
            telemetry,
            RoomTelemetryTagSerializer(telemetry, many=True).data,
            lambda row: tag_types.get((row["entity_id"], TELEMETRY, None, row["key__key"])),
        ),
    ]
