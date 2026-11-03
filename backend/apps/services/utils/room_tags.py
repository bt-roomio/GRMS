import json
import logging
from typing import NamedTuple

from django.db.models import F

from rest_framework.exceptions import NotFound

from main.models import Room
from services.mapping.constants import Source
from services.mapping.resolver import TagMapper, Target, device_target
from services.serializers.device_tag_types import ATTRIBUTE, TAG_TYPES_KEY, TELEMETRY
from services.serializers.tag import RoomAttributeTagSerializer, RoomTelemetryTagSerializer, TagSerializer
from services.utils.composite_tags import (
    Binding,
    InputIndex,
    InputRow,
    composite_fields,
    has_inputs,
    input_index,
    virtual_tag_id,
    virtual_tag_room_id,
)
from shuttle.models import AttributeKv, TsKvLatest

logger = logging.getLogger(__name__)


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


class RoomTags(NamedTuple):
    """The room's tags in the integrator's form, with what composite mapping needs of them."""

    tags: list[dict]
    composites: dict[str, Binding]  # tag id -> the composite rule computing the tag
    index: InputIndex  # the room's tags in GRMS form, as composite inputs

    def get(self, tag_id) -> dict | None:
        return next((tag for tag in self.tags if tag["id"] == str(tag_id)), None)


def _grms_tags(room, tenant, names=None) -> list[tuple[dict, InputRow]]:
    """The room's CLIENT_SCOPE attributes and latest telemetry in GRMS form, each part ordered by
    key, with ``tag_type`` and ``tag_ranges`` from their device's ``TAG_TYPES``; only the tags
    called one of ``names`` when given."""
    # A device-reported CLIENT_SCOPE TAG_TYPES is configuration, not a tag.
    attributes = AttributeKv.objects.get_attributes_by_room(
        room, AttributeKv.CLIENT_SCOPE, sort_by=("attribute_key", "id")
    ).exclude(attribute_key=TAG_TYPES_KEY)
    telemetry = TsKvLatest.objects.get_ts_kv_latest_by_room(room, tenant, sort_by=("key__key", "id"))
    if names is not None:
        attributes = attributes.filter(attribute_key__in=names)
        telemetry = telemetry.filter(key__key__in=names)
    attributes, telemetry = list(attributes), list(telemetry)
    tag_types = _tag_types_by_tag({row["entity_id"] for row in [*attributes, *telemetry]})
    parts = (
        (
            attributes,
            RoomAttributeTagSerializer,
            Source.ATTRIBUTE,
            "last_update_ts",
            ATTRIBUTE,
            AttributeKv.CLIENT_SCOPE,
        ),
        (telemetry, RoomTelemetryTagSerializer, Source.TELEMETRY, "ts", TELEMETRY, None),
    )
    result = []
    for rows, serializer, source, ts_field, section, sub_section in parts:
        for row, tag in zip(rows, serializer(rows, many=True).data, strict=True):
            tag.update(_tag_type_fields(tag_types.get((row["entity_id"], section, sub_section, tag["tag_name"]))))
            input_row = InputRow(
                row["id"], row["entity_id"], source, tag["tag_name"], tag["value"], row[ts_field], tag["tag_ranges"]
            )
            result.append((tag, input_row))
    return result


def _room_device_ids(room) -> set:
    return set(room.devices.values_list("id", flat=True))


def _bind_composites(
    room, grms, index: InputIndex, mapper: TagMapper, device_ids
) -> dict[str, tuple[Binding, dict | None]]:
    """The room's composite tags: tag id -> (the rule computing it, the physical tag it computes or
    ``None`` for a virtual one). A rule computes the one physical tag of the room named as its
    output (on its device, for a device profile's rule). A rule whose output names other tags of
    the room (several, or only on another device) computes none: a virtual tag would repeat a name
    the room already has. Otherwise the room gets a virtual tag when it has any of the inputs."""
    bound: dict[str, tuple[Binding, dict | None]] = {}
    for rule, device_id in mapper.composites_for_room(room.type_id, device_ids):
        binding = Binding(rule, device_id)
        name = rule["output"]["tag_name"]
        named = [(tag, row) for tag, row in grms if tag["tag_name"] == name]
        own = [tag for tag, row in named if device_id is None or row.entity_id == device_id]
        if len(own) == 1:
            bound[own[0]["id"]] = (binding, own[0])
        elif named:
            logger.warning(
                "Composite rule %r: room %s has %s tags named %r on its devices; none is computed.",
                rule["id"],
                room.pk,
                len(named),
                name,
            )
        elif has_inputs(binding, index):
            bound[virtual_tag_id(room.id, rule["id"])] = (binding, None)
    return bound


def _composite_tag_data(tag_id: str, binding: Binding, physical: dict | None, index: InputIndex) -> dict:
    """The tag a composite rule computes in the integrator's form; a computed physical tag keeps
    its id and name, and its ``tag_type`` unless the rule names one."""
    fields = composite_fields(binding, index)
    if physical is None:
        return {"id": tag_id, "tag_name": binding.rule["output"]["tag_name"], **fields, "virtual": True}
    physical.update(
        value=fields["value"],
        tag_ranges=fields["tag_ranges"],
        tag_type=fields["tag_type"] or physical["tag_type"],
        updated_at=fields["updated_at"] or physical["updated_at"],
    )
    return physical


def build_room_tags(room, tenant, mapper: TagMapper | None = None) -> RoomTags:
    """The room's tags in the integrator's form: its attributes and telemetry, then the virtual tags
    of its composite rules (see ``_bind_composites``)."""
    mapper = mapper or TagMapper()
    grms = _grms_tags(room, tenant)
    index = input_index(row for _, row in grms)
    device_ids = _room_device_ids(room) if mapper.composites else set()

    composites: dict[str, Binding] = {}
    virtual = []
    for tag_id, (binding, physical) in _bind_composites(room, grms, index, mapper, device_ids).items():
        data = _composite_tag_data(tag_id, binding, physical, index)
        composites[tag_id] = binding
        if physical is None:
            virtual.append(data)

    tags = []
    for tag, row in grms:
        if tag["id"] not in composites:
            mapper.tag_to_external(tag, Target(row.entity_id, room.type_id))
        tags.append(tag)
    tags += sorted(virtual, key=lambda tag: tag["tag_name"])
    return RoomTags(tags, composites, index)


def room_tags(room, tenant, mapper: TagMapper | None = None) -> list[dict]:
    """The room's tags as one list, shared by the REST view and the WebSocket consumer so both
    return the same shape. ``mapper`` converts values and ranges to the integration's form; none
    leaves GRMS values."""
    return build_room_tags(room, tenant, mapper).tags


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


class ResolvedTag(NamedTuple):
    """A tag found by id. ``model`` is the AttributeKv/TsKvLatest behind a plain or computed tag; a
    composite tag (virtual or computed) has ``binding`` and the room's ``index`` of inputs.
    ``watch`` lists the ``(entity ids, tag names)`` whose updates change the tag."""

    data: dict
    model: AttributeKv | TsKvLatest | None
    binding: Binding | None
    index: InputIndex | None
    watch: tuple[set[str], set[str]]


def _rooms(tenant):
    return Room.objects.by_tenant(tenant).annotate(type_name=F("type__title"))


def _physical_tag(tenant, tag_id):
    """A tag id may reference an AttributeKv (attribute) or a TsKvLatest (telemetry)."""
    tag = AttributeKv.objects.select_related("entity__room").filter(entity__tenant=tenant, pk=tag_id).first()
    if tag is None:
        tag = TsKvLatest.objects.select_related("entity__room", "key").filter(entity__tenant=tenant, pk=tag_id).first()
    return tag


def _virtual_tag_room(tenant, mapper: TagMapper, tag_id):
    """The room whose virtual tag may have this id: one candidate room per composite rule id."""
    rule_ids = {rule_id for rules in mapper.composites.values() for rule_id in rules}
    if not rule_ids:
        return None
    return _rooms(tenant).filter(pk__in={virtual_tag_room_id(tag_id, rule_id) for rule_id in rule_ids}).first()


def _composite_tag(room, tenant, mapper: TagMapper, tag_id, model=None) -> ResolvedTag | None:
    """The composite tag of this id in the room, or ``None``. Reads only the room's tags that
    composite rules use, not the whole tag list."""
    names = set(mapper.composite_outputs)
    names |= {
        item["tag_name"] for rules in mapper.composites.values() for rule in rules.values() for item in rule["inputs"]
    }
    grms = _grms_tags(room, tenant, names)
    index = input_index(row for _, row in grms)
    device_ids = _room_device_ids(room)
    found = _bind_composites(room, grms, index, mapper, device_ids).get(str(tag_id))
    if found is None:
        return None
    binding, physical = found
    data = _composite_tag_data(str(tag_id), binding, physical, index)
    watched = {item["tag_name"] for item in binding.rule["inputs"]} | {
        binding.rule["output"]["tag_name"],
        TAG_TYPES_KEY,
    }
    return ResolvedTag(data, model, binding, index, ({str(device_id) for device_id in device_ids}, watched))


def resolve_tag(tenant, tag_id, mapper: TagMapper) -> ResolvedTag:
    """A tag of the tenant by id in the integrator's form: a plain attribute or telemetry tag, one
    a composite rule computes, or a virtual one. Raises ``NotFound``."""
    model = _physical_tag(tenant, tag_id)
    if model is not None:
        name = model.attribute_key if isinstance(model, AttributeKv) else model.key.key
        room_id = model.entity.room_id
        if room_id is not None and name in mapper.composite_outputs:
            # An inactive room has no composite tags: its tags stay plain.
            room = _rooms(tenant).filter(pk=room_id).first()
            if room is not None and (resolved := _composite_tag(room, tenant, mapper, tag_id, model)) is not None:
                return resolved
        return ResolvedTag(
            tag_with_type(model, mapper), model, None, None, ({str(model.entity_id)}, {name, TAG_TYPES_KEY})
        )
    room = _virtual_tag_room(tenant, mapper, tag_id)
    if room is not None and (resolved := _composite_tag(room, tenant, mapper, tag_id)) is not None:
        return resolved
    raise NotFound("Tag not found.")


def room_input_index(room, tenant) -> InputIndex:
    """The room's tags in GRMS form as composite inputs, without building the tag list."""
    return input_index(row for _, row in _grms_tags(room, tenant))
