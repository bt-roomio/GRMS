"""Connector-agnostic core for the *devices-from-configuration* flow.

Both the Roomio and KNX configuration formats ultimately need to produce the
same result: ``Device`` rows, ``TsKvDictionary`` / ``TsKvLatest`` (timeseries),
``AttributeKv`` (attributes + attribute-updates) and ``Relation`` links to a
gateway.  The two formats differ only in *how* they describe devices and tags:

* Roomio is normalized   -- devices reference shared ``addressMaps`` by id.
* KNX is denormalized     -- each device lists its own tags inline.

Each connector reduces its raw payload to a list of :class:`CanonicalDevice`
(via a thin adapter) and hands it to :func:`create_devices_from_config`, which
owns the idempotent bulk-upsert logic exactly once.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from django.db import transaction

from rest_framework import serializers

from main.models import Device, DeviceProfile
from shuttle.models import AttributeKv, Relation, TsKvDictionary, TsKvLatest

DEFAULT_PROFILE_NAME = "Default"


@dataclass
class CanonicalDevice:
    """One device entry in the connector-agnostic intermediate representation.

    A ``name`` may legitimately repeat across entries (e.g. the same Roomio MAC
    referencing several address maps); device creation deduplicates by name
    while tag creation iterates entries.
    """

    name: str
    profile_name: str = DEFAULT_PROFILE_NAME
    timeseries: list[str] = field(default_factory=list)
    attributes: list[str] = field(default_factory=list)
    attribute_updates: list[str] = field(default_factory=list)


def get_active_gateway(tenant, gateway_id) -> Device | None:
    return Device.objects.filter(
        id=gateway_id,
        tenant=tenant,
        is_active=True,
        additional_info__gateway=True,
    ).first()


@transaction.atomic
def create_devices_from_config(*, tenant, gateway: Device, devices: list[CanonicalDevice]) -> dict:
    """Create devices, timeseries, attributes and gateway relations.

    Idempotent: re-running with the same canonical devices does not duplicate
    rows.  Connector-agnostic -- it knows nothing about Roomio or KNX.
    """

    # 1) Resolve device profiles by name (cached, one query per distinct name).
    profile_cache: dict[str, DeviceProfile] = {}

    def resolve_profile(profile_name: str) -> DeviceProfile:
        name = profile_name or DEFAULT_PROFILE_NAME
        if name not in profile_cache:
            profile, _ = DeviceProfile.objects.get_or_create(
                tenant=tenant,
                name__iexact=name,
                defaults={"name": name},
            )
            profile_cache[name] = profile
        return profile_cache[name]

    # 2) Unique device names (preserve order), remembering each name's profile.
    name_to_profile: dict[str, str] = {}
    for dev in devices:
        name_to_profile.setdefault(dev.name, dev.profile_name)
    unique_names = list(name_to_profile)

    # 3) Bulk-create any new Devices.
    existing_names = set(
        Device.objects.filter(tenant=tenant, name__in=unique_names, is_active=True).values_list("name", flat=True)
    )
    to_create = [
        Device(
            name=name,
            tenant=tenant,
            is_active=True,
            device_profile=resolve_profile(name_to_profile[name]),
            type="default",
        )
        for name in unique_names
        if name not in existing_names
    ]
    if to_create:
        Device.objects.bulk_create(to_create, ignore_conflicts=True)

    # Always re-fetch so dev_map is complete (covers pre-existing + new).
    dev_map = {d.name: d for d in Device.objects.filter(tenant=tenant, name__in=unique_names, is_active=True)}

    # 4) Upsert TsKvDictionary for every distinct timeseries tag.
    all_ts_tags = {tag for dev in devices for tag in dev.timeseries}
    dict_map = {d.key: d for d in TsKvDictionary.objects.filter(key__in=all_ts_tags)}
    missing = all_ts_tags - dict_map.keys()
    if missing:
        TsKvDictionary.objects.bulk_create([TsKvDictionary(key=tag) for tag in missing], ignore_conflicts=True)
        for d in TsKvDictionary.objects.filter(key__in=missing):
            dict_map[d.key] = d

    # 5) Build deduped TsKvLatest (one per device x timeseries tag).
    latest_objs: list[TsKvLatest] = []
    seen_ts: set[tuple] = set()
    for dev in devices:
        device = dev_map[dev.name]
        for tag in dev.timeseries:
            ts_obj = dict_map[tag]
            key = (device.id, ts_obj.key_id)
            if key in seen_ts:
                continue
            seen_ts.add(key)
            latest_objs.append(TsKvLatest(entity_id=device.id, key=ts_obj, long_v=0))

    ts_created = 0
    if latest_objs:
        existing_ts = set(
            TsKvLatest.objects.filter(entity_id__in={o.entity_id for o in latest_objs}).values_list(
                "entity_id", "key_id"
            )
        )
        latest_objs = [o for o in latest_objs if (o.entity_id, o.key.key_id) not in existing_ts]
        if latest_objs:
            TsKvLatest.objects.bulk_create(latest_objs, ignore_conflicts=True)
            ts_created = len(latest_objs)

    # 6) Build deduped AttributeKv (attribute_updates -> SHARED, attributes -> CLIENT).
    attr_objs: list[AttributeKv] = []
    seen_attrs: set[tuple] = set()

    def queue_attr(device: Device, attribute_type: str, attribute_key: str) -> None:
        key = ("DEVICE", attribute_type, device.id, attribute_key)
        if key in seen_attrs:
            return
        seen_attrs.add(key)
        attr_objs.append(
            AttributeKv(
                entity_type="DEVICE",
                attribute_type=attribute_type,
                attribute_key=attribute_key,
                entity_id=device.id,
                long_v=0,
            )
        )

    for dev in devices:
        device = dev_map[dev.name]
        for tag in dev.attribute_updates:
            queue_attr(device, "SHARED_SCOPE", tag)
        for tag in dev.attributes:
            queue_attr(device, "CLIENT_SCOPE", tag)

    attrs_created = 0
    if attr_objs:
        existing_attrs = set(
            AttributeKv.objects.filter(
                entity_type="DEVICE",
                entity_id__in={o.entity_id for o in attr_objs},
            ).values_list("entity_type", "attribute_type", "entity_id", "attribute_key")
        )
        attr_objs = [
            o
            for o in attr_objs
            if (o.entity_type, o.attribute_type, o.entity_id, o.attribute_key) not in existing_attrs
        ]
        if attr_objs:
            AttributeKv.objects.bulk_create(attr_objs, ignore_conflicts=True)
            attrs_created = len(attr_objs)

    # 7) Link every (non-gateway) device to the gateway.
    relation_objs = [
        Relation(
            from_id=gateway,
            from_type="DEVICE",
            relation_type_group="COMMON",
            relation_type="Created",
            to_id=dev_map[name],
            to_type="DEVICE",
        )
        for name in unique_names
        if dev_map[name].id != gateway.id
    ]
    if relation_objs:
        Relation.objects.bulk_create(relation_objs, ignore_conflicts=True)

    return {
        "device_names": unique_names,
        "devices_created": len(to_create),
        "ts_latest_created": ts_created,
        "attributes_created": attrs_created,
        "relations_created": len(relation_objs),
    }


def require_active_gateway(tenant, gateway_id) -> Device:
    """Resolve the gateway or raise a serializer ValidationError (shared by views)."""

    gateway = get_active_gateway(tenant, gateway_id)
    if not gateway:
        raise serializers.ValidationError({"gateway_id": "Gateway not found or not an active gateway for this tenant."})
    return gateway
