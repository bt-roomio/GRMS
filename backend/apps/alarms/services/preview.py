"""
Dry run of a profile's rules against the devices it already has.

The guard rail for the risk this feature carries: a rule that matches 300 of
300 devices is visible before it is saved, not after 300 alarms have been
raised and pushed to Telegram.
"""

from alarms.constants import SEVERITY_ORDER
from alarms.services.details import render
from alarms.services.engine import build_snapshots, collect_keys
from alarms.services.predicates import eval_condition
from main.models import Device

SAMPLE_SIZE = 5


def preview(profile_id, alarms: list[dict]) -> dict:
    devices = list(Device.objects.filter(is_active=True, device_profile_id=profile_id).select_related("room"))
    ts_keys, attr_keys = collect_keys(alarms)
    snapshots = build_snapshots(devices, ts_keys, attr_keys)

    return {
        "device_count": len(devices),
        "alarms": [preview_alarm(alarm, devices, snapshots) for alarm in alarms],
    }


def preview_alarm(alarm: dict, devices, snapshots) -> dict:
    create_rules = alarm.get("createRules") or {}
    severities = []

    for severity in SEVERITY_ORDER:
        rule = create_rules.get(severity)
        if not rule:
            continue
        severities.append(
            {
                "severity": severity,
                # The spec is deliberately ignored: DURATION and REPEATING are
                # about time, and a preview only knows about now.
                "spec": (rule.get("condition") or {}).get("spec", {}).get("type"),
                **matching(rule, alarm, severity, devices, snapshots),
            }
        )

    clear_rule = alarm.get("clearRule")
    return {
        "alarmType": alarm.get("alarmType"),
        "create_rules": severities,
        "clear_rule": matching(clear_rule, alarm, "CLEAR", devices, snapshots) if clear_rule else None,
    }


def matching(rule: dict, alarm: dict, severity: str, devices, snapshots) -> dict:
    filters = (rule.get("condition") or {}).get("condition") or []
    matched = []

    for device in devices:
        snapshot = snapshots[device.id]
        if eval_condition(filters, snapshot):
            matched.append(
                {
                    "id": str(device.id),
                    "name": device.name,
                    "room": snapshot.room_number,
                    "message": render(rule.get("alarmDetails"), snapshot, alarm.get("alarmType", ""), severity),
                }
            )

    return {"matched_count": len(matched), "sample": matched[:SAMPLE_SIZE]}
