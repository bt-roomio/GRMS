"""
The evaluator: one pass over every device of every profile that has rules.

Why periodic rather than in the hot path — a DURATION condition ("``active``
has been false for ten minutes") cannot be noticed by an incoming message; it
needs a timer. Once a timer exists, intercepting telemetry in
``_process_telemetry_entries`` buys nothing: ``TsKvLatest`` already *is* "the
last value per (device, key)". The cost is a delay of at most one tick, and the
hot path stays untouched.
"""

import logging
from collections.abc import Iterable, Iterator
from datetime import datetime
from itertools import islice
from typing import Any
from uuid import UUID

from django.utils import timezone

from alarms.constants import (
    ATTRIBUTES_KEY,
    KEY_ATTRIBUTE,
    KEY_TIME_SERIES,
    SOURCE_CURRENT_DEVICE,
)
from alarms.models import Alarm, AlarmRule, AlarmRuleState
from alarms.services import state as rule_state
from alarms.services.snapshot import DataSnapshot
from main.models import Device, Tenant
from shuttle.models import AttributeKv, TsKvDictionary, TsKvLatest

logger = logging.getLogger(__name__)

DEVICE_CHUNK = 500

VALUE_FIELDS = ("bool_v", "str_v", "long_v", "dbl_v", "json_v")


class EvaluationResult:
    def __init__(self):
        self.devices = 0
        self.rules = 0
        self.created: list[Alarm] = []
        self.cleared: list[Alarm] = []
        self.escalated: list[Alarm] = []

    @property
    def touched_tenant_ids(self) -> set[UUID]:
        return {alarm.tenant_id for alarm in (*self.created, *self.cleared, *self.escalated)}

    def __str__(self) -> str:
        return (
            f"{self.devices} devices × {self.rules} rules → "
            f"{len(self.created)} created, {len(self.escalated)} escalated, {len(self.cleared)} cleared"
        )


# --------------------------------------------------------------------------
# Rule introspection
# --------------------------------------------------------------------------


def load_rules(profile_ids=None) -> dict[UUID, list[dict]]:
    """
    Enabled rules of live profiles, grouped by profile.

    GRMS deviation: TB keeps rules in ``DeviceProfile.profile_data["alarms"]``.
    Here they are rows, so one query returns exactly the rules that may fire —
    ``enabled`` and ``active`` are filtered in SQL instead of in Python after
    loading every profile.
    """
    grouped: dict[UUID, list[dict]] = {}
    for rule in AlarmRule.objects.active().for_profiles(profile_ids):
        grouped.setdefault(rule.device_profile_id, []).append(rule.as_rule())
    return grouped


def iter_rules(alarm: dict) -> Iterator[dict]:
    create_rules = alarm.get("createRules")
    if isinstance(create_rules, dict):
        yield from (rule for rule in create_rules.values() if isinstance(rule, dict))

    if isinstance(alarm.get("clearRule"), dict):
        yield alarm["clearRule"]


def collect_keys(alarms: Iterable[dict]) -> tuple[set[str], set[str]]:
    """
    Every telemetry and attribute key the given rules can possibly read.

    Defensive throughout: this runs before the per-rule guard in
    ``evaluate_chunk``, so a rule written before the validator existed must not
    be able to abort the whole pass here.
    """
    ts_keys: set[str] = set()
    attr_keys: set[str] = set()

    for alarm in alarms:
        for rule in iter_rules(alarm):
            condition = rule.get("condition")
            if not isinstance(condition, dict):
                continue

            filters = condition.get("condition")
            for condition_filter in filters if isinstance(filters, list) else []:
                if not isinstance(condition_filter, dict):
                    continue

                key = condition_filter.get("key")
                key = key if isinstance(key, dict) else {}
                name = key.get("key")
                if not name:
                    continue
                if key.get("type") == KEY_TIME_SERIES:
                    ts_keys.add(name)
                elif key.get("type") == KEY_ATTRIBUTE:
                    attr_keys.add(name)

                predicate = condition_filter.get("predicate")
                attr_keys |= device_attributes_of(predicate if isinstance(predicate, dict) else {})

            spec = condition.get("spec")
            attr_keys |= device_attributes_of_value(spec.get("predicate") if isinstance(spec, dict) else None)

    return ts_keys, attr_keys


def device_attributes_of(predicate: dict, depth: int = 1) -> set[str]:
    """Attribute keys a predicate's dynamicValue may look up on the device."""
    if depth > 10:
        return set()

    if predicate.get("predicates"):
        found: set[str] = set()
        for child in predicate["predicates"]:
            found |= device_attributes_of(child, depth + 1)
        return found

    return device_attributes_of_value(predicate.get("value"))


def device_attributes_of_value(predicate_value: Any) -> set[str]:
    if not isinstance(predicate_value, dict):
        return set()
    dynamic = predicate_value.get("dynamicValue") or {}
    # ``inherit`` starts at the declared source, so anything but a device source
    # never reaches attribute_kv.
    if dynamic.get("sourceType") == SOURCE_CURRENT_DEVICE and dynamic.get("sourceAttribute"):
        return {dynamic["sourceAttribute"]}
    return set()


# --------------------------------------------------------------------------
# Snapshot assembly
# --------------------------------------------------------------------------


def entity_fields(device: Device) -> dict[str, Any]:
    fields = {
        "name": device.name,
        "type": device.type,
        "label": device.label,
        "status": device.status,
        "is_active": device.is_active,
        "is_gateway": bool((device.additional_info or {}).get("gateway")),
    }
    if device.room_id:
        fields |= {
            "room.number": device.room.number,
            "room.floor": device.room.floor,
            "room.state": device.room.state,
        }
    return fields


def attributes_of(instance) -> dict[str, Any]:
    """
    GRMS deviation: tenants and rooms have no ``attribute_kv`` row, so a
    DynamicValue reads their overrides out of ``additional_info["attributes"]``.
    """
    info = getattr(instance, "additional_info", None)
    if not isinstance(info, dict):
        return {}
    attributes = info.get(ATTRIBUTES_KEY)
    return attributes if isinstance(attributes, dict) else {}


def build_snapshots(devices: list[Device], ts_keys: set[str], attr_keys: set[str]) -> dict[UUID, DataSnapshot]:
    device_ids = [device.id for device in devices]

    key_names = {}
    if ts_keys:
        key_names = dict(TsKvDictionary.objects.filter(key__in=ts_keys).values_list("key_id", "key"))

    snapshots = {}
    for device in devices:
        snapshots[device.id] = DataSnapshot(
            device_id=device.id,
            tenant_id=device.tenant_id,
            room_id=device.room_id,
            device_name=device.name,
            room_number=device.room.number if device.room_id else None,
            fields=entity_fields(device),
            room_attrs=attributes_of(device.room) if device.room_id else {},
        )

    if key_names:
        rows = TsKvLatest.objects.filter(entity_id__in=device_ids, key_id__in=key_names).values(
            "entity_id", "key_id", "ts", *VALUE_FIELDS
        )
        for row in rows:
            snapshot = snapshots.get(row["entity_id"])
            if snapshot is not None:
                snapshot.ts[key_names[row["key_id"]]] = row

    if attr_keys:
        rows = AttributeKv.objects.filter(
            entity_id__in=device_ids,
            attribute_type=AttributeKv.SERVER_SCOPE,
            attribute_key__in=attr_keys,
        ).values("entity_id", "attribute_key", "last_update_ts", *VALUE_FIELDS)
        for row in rows:
            snapshot = snapshots.get(row["entity_id"])
            if snapshot is not None:
                snapshot.attrs[row["attribute_key"]] = row

    attach_hierarchy(snapshots.values())
    return snapshots


def attach_hierarchy(snapshots: Iterable[DataSnapshot]) -> None:
    """
    Attach the attribute overrides that live above the device.

    Only the tenant, because the room's attributes come along with the device's
    own ``select_related`` in ``build_snapshots``.
    """
    snapshots = list(snapshots)
    tenant_ids = {snapshot.tenant_id for snapshot in snapshots if snapshot.tenant_id}
    if not tenant_ids:
        return

    tenants = {tenant.id: attributes_of(tenant) for tenant in Tenant.objects.filter(id__in=tenant_ids)}
    for snapshot in snapshots:
        snapshot.tenant_attrs = tenants.get(snapshot.tenant_id, {})


# --------------------------------------------------------------------------
# The pass
# --------------------------------------------------------------------------


def chunked(items: list, size: int) -> Iterator[list]:
    iterator = iter(items)
    while chunk := list(islice(iterator, size)):
        yield chunk


def evaluate(now: datetime | None = None, profile_ids=None, device_ids=None) -> EvaluationResult:
    now = now or timezone.now()
    result = EvaluationResult()

    rules_by_profile = load_rules(profile_ids)
    if not rules_by_profile:
        return result

    result.rules = sum(len(rules) for rules in rules_by_profile.values())

    devices_query = Device.objects.filter(is_active=True, device_profile_id__in=rules_by_profile).select_related("room")
    if device_ids:
        devices_query = devices_query.filter(id__in=device_ids)

    all_devices = list(devices_query)
    result.devices = len(all_devices)

    for chunk in chunked(all_devices, DEVICE_CHUNK):
        evaluate_chunk(chunk, rules_by_profile, now, result)

    if result.touched_tenant_ids:
        from alarms.observables.alarm import publish_alarms

        publish_alarms(result.touched_tenant_ids)

    return result


def evaluate_chunk(devices: list[Device], rules_by_profile: dict, now: datetime, result: EvaluationResult) -> None:
    rules = [rule for device in devices for rule in rules_by_profile.get(device.device_profile_id, [])]
    ts_keys, attr_keys = collect_keys(rules)
    snapshots = build_snapshots(devices, ts_keys, attr_keys)

    device_ids = [device.id for device in devices]
    alarm_types = {rule["alarmType"] for rule in rules}

    active_alarms = {
        (alarm.originator_id, alarm.alarm_type): alarm
        for alarm in Alarm.objects.filter(originator_id__in=device_ids, cleared=False, alarm_type__in=alarm_types)
    }
    states = {
        (row.device_id, row.alarm_rule_type): row
        for row in AlarmRuleState.objects.filter(device_id__in=device_ids, alarm_rule_type__in=alarm_types)
    }

    to_update, to_create, to_delete = [], [], []

    for device in devices:
        snapshot = snapshots[device.id]
        for rule in rules_by_profile.get(device.device_profile_id, []):
            alarm_type = rule["alarmType"]
            row = states.get((device.id, alarm_type))

            try:
                outcome = rule_state.process(
                    rule,
                    snapshot,
                    now,
                    active_alarms.get((device.id, alarm_type)),
                    (row.state if row else None) or {},
                )
            except Exception:
                # One malformed rule must not take the whole installation's
                # evaluation down with it.
                logger.exception("Alarm rule '%s' failed on device %s", alarm_type, device.id)
                continue

            if outcome.created:
                result.created.append(outcome.created)
                active_alarms[(device.id, alarm_type)] = outcome.created
            if outcome.escalated:
                result.escalated.append(outcome.escalated)
            if outcome.cleared:
                result.cleared.append(outcome.cleared)
                active_alarms.pop((device.id, alarm_type), None)

            if outcome.state:
                if row:
                    row.state = outcome.state
                    # bulk_update writes the attribute as given; auto_now does
                    # not fire for it, so the stamp is set by hand.
                    row.updated_at = now
                    to_update.append(row)
                else:
                    to_create.append(AlarmRuleState(device=device, alarm_rule_type=alarm_type, state=outcome.state))
            elif row:
                to_delete.append(row.id)

    persist_states(to_create, to_update, to_delete)


def persist_states(to_create, to_update, to_delete) -> None:
    if to_create:
        AlarmRuleState.objects.bulk_create(to_create, ignore_conflicts=True)
    if to_update:
        AlarmRuleState.objects.bulk_update(to_update, ["state", "updated_at"])
    if to_delete:
        AlarmRuleState.objects.filter(id__in=to_delete).delete()
