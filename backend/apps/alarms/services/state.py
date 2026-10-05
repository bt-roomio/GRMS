"""
One rule against one device — the port of TB's ``AlarmState.process``.

Order of business, unchanged from TB: create rules are probed from CRITICAL
down and the first match wins; only if none matched does the clear rule get a
look. Everything else — dedup, escalation, the audit trail — falls out of that.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime

from django.db import transaction

from alarms.constants import SEVERITY_ORDER, SEVERITY_RANK
from alarms.models import Alarm, AlarmComment, AlarmRuleState
from alarms.services.details import matched_values, render
from alarms.services.predicates import eval_condition
from alarms.services.propagate import propagation_targets
from alarms.services.schedule import is_active_at
from alarms.services.snapshot import DataSnapshot
from alarms.services.spec import eval_spec

logger = logging.getLogger(__name__)


@dataclass
class RuleOutcome:
    state: dict = field(default_factory=dict)
    created: Alarm | None = None
    cleared: Alarm | None = None
    escalated: Alarm | None = None

    @property
    def changed(self) -> bool:
        return bool(self.created or self.cleared or self.escalated)


def process(rule: dict, snapshot: DataSnapshot, now: datetime, active_alarm: Alarm | None, state: dict) -> RuleOutcome:
    outcome = RuleOutcome()
    create_rules = rule.get("createRules") or {}

    for severity in SEVERITY_ORDER:
        create_rule = create_rules.get(severity)
        if not create_rule:
            continue

        if not is_active_at(create_rule.get("schedule"), now):
            # Outside its schedule the rule does not exist — and neither does
            # the streak it was building.
            continue

        condition = create_rule.get("condition") or {}
        filters = condition.get("condition") or []
        matched = eval_condition(filters, snapshot)
        fired, sub_state = eval_spec(condition.get("spec"), state.get(severity), matched, now, snapshot)

        if sub_state:
            outcome.state[severity] = sub_state

        if fired:
            _raise(rule, create_rule, severity, filters, snapshot, now, active_alarm, outcome)
            return outcome

    if active_alarm and rule.get("clearRule"):
        _try_clear(rule["clearRule"], snapshot, now, active_alarm, state, outcome)

    return outcome


def _raise(rule, create_rule, severity, filters, snapshot, now, active_alarm, outcome):
    message = render(create_rule.get("alarmDetails"), snapshot, rule["alarmType"], severity)
    details = {"message": message, "values": matched_values(filters, snapshot)}

    if active_alarm is None:
        outcome.created = _create(rule, severity, snapshot, now, details)
        return

    updates = ["end_ts", "details", "updated_at"]
    active_alarm.end_ts = now
    active_alarm.details = details

    if SEVERITY_RANK[severity] < SEVERITY_RANK[active_alarm.severity]:
        previous = active_alarm.severity
        active_alarm.severity = severity
        updates.append("severity")
        outcome.escalated = active_alarm
        AlarmComment.objects.create(
            alarm=active_alarm,
            alarm_comment_type=AlarmComment.TYPE.SYSTEM,
            comment={
                "subtype": AlarmComment.SUBTYPE.SEVERITY_CHANGED,
                "from": previous,
                "to": severity,
                "text": f"Severity changed from {previous} to {severity}",
            },
        )

    active_alarm.save(update_fields=updates)


def _create(rule, severity, snapshot, now, details) -> Alarm:
    alarm, created = Alarm.objects.get_or_create(
        originator_id=snapshot.device_id,
        alarm_type=rule["alarmType"],
        cleared=False,
        defaults={
            "tenant_id": snapshot.tenant_id,
            "room_id": snapshot.room_id,
            "severity": severity,
            "start_ts": now,
            "end_ts": now,
            "details": details,
            "propagate": bool(rule.get("propagate")),
            "propagate_relation_types": rule.get("propagateRelationTypes") or [],
            "propagate_to_owner": bool(rule.get("propagateToOwner")),
            "propagate_to_tenant": bool(rule.get("propagateToTenant")),
            "propagate_entity_ids": propagation_targets(rule, snapshot.device_id, snapshot.room_id, snapshot.tenant_id),
        },
    )

    if not created:
        # Lost the race with the other detector; the partial unique index did
        # its job and this tick simply refreshes the row.
        alarm.end_ts = now
        alarm.details = details
        alarm.save(update_fields=["end_ts", "details", "updated_at"])
        return alarm

    return alarm


def _try_clear(clear_rule, snapshot, now, active_alarm, state, outcome):
    if not is_active_at(clear_rule.get("schedule"), now):
        return

    condition = clear_rule.get("condition") or {}
    matched = eval_condition(condition.get("condition") or [], snapshot)
    fired, sub_state = eval_spec(condition.get("spec"), state.get(AlarmRuleState.CLEAR_KEY), matched, now, snapshot)

    if sub_state:
        outcome.state[AlarmRuleState.CLEAR_KEY] = sub_state

    if fired:
        clear_alarm(active_alarm, now)
        outcome.cleared = active_alarm


@transaction.atomic
def clear_alarm(alarm: Alarm, now: datetime, user=None, text: str | None = None) -> Alarm:
    alarm.cleared = True
    alarm.clear_ts = now
    alarm.save(update_fields=["cleared", "clear_ts", "updated_at"])

    AlarmComment.objects.create(
        alarm=alarm,
        user=user,
        alarm_comment_type=AlarmComment.TYPE.SYSTEM,
        comment={"subtype": AlarmComment.SUBTYPE.CLEARED, "text": text or "Alarm cleared"},
    )
    return alarm


@transaction.atomic
def acknowledge_alarm(alarm: Alarm, now: datetime, user=None) -> Alarm:
    if alarm.acknowledged:
        return alarm

    alarm.acknowledged = True
    alarm.ack_ts = now
    alarm.save(update_fields=["acknowledged", "ack_ts", "updated_at"])

    AlarmComment.objects.create(
        alarm=alarm,
        user=user,
        alarm_comment_type=AlarmComment.TYPE.SYSTEM,
        comment={"subtype": AlarmComment.SUBTYPE.ACKNOWLEDGED, "text": "Alarm acknowledged"},
    )
    return alarm


@transaction.atomic
def assign_alarm(alarm: Alarm, now: datetime, assignee=None, user=None) -> Alarm:
    alarm.assignee = assignee
    alarm.assign_ts = now if assignee else None
    alarm.save(update_fields=["assignee", "assign_ts", "updated_at"])

    AlarmComment.objects.create(
        alarm=alarm,
        user=user,
        alarm_comment_type=AlarmComment.TYPE.SYSTEM,
        comment={
            "subtype": AlarmComment.SUBTYPE.ASSIGNED if assignee else AlarmComment.SUBTYPE.UNASSIGNED,
            "assignee": str(assignee.id) if assignee else None,
            "text": f"Assigned to {assignee.email}" if assignee else "Unassigned",
        },
    )
    return alarm
