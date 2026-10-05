from typing import ClassVar, cast
from uuid import UUID

from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.db.models import CASCADE, SET_NULL
from django.utils import timezone

from alarms.constants import AlarmSeverity, AlarmStatus
from alarms.querysets.alarm import AlarmQuerySet
from alarms.querysets.alarm_comment import AlarmCommentQuerySet
from alarms.querysets.rule_state import AlarmRuleStateQuerySet
from core.models import BaseModel, UpdateByModel


class Alarm(BaseModel, UpdateByModel):
    """
    One incident, ported from ``org.thingsboard.server.common.data.alarm.Alarm``.

    The row *is* the journal: ``start_ts`` is when the condition first held,
    ``end_ts`` the last tick it still held, ``clear_ts`` when it stopped. There is
    no separate event table — "how long was the gateway on floor 3 down" is
    ``clear_ts - start_ts`` on a single row.
    """

    tenant = models.ForeignKey("main.Tenant", CASCADE, related_name="alarms")
    originator = models.ForeignKey("main.Device", CASCADE, related_name="alarms")
    # Denormalised from the originator so the journal survives a device moving
    # rooms, and so room filters stay single-table.
    room = models.ForeignKey("main.Room", SET_NULL, null=True, blank=True, related_name="alarms")

    alarm_type = models.CharField(max_length=255)  # DeviceProfileAlarm.alarmType
    severity = models.CharField(max_length=16, choices=AlarmSeverity.choices)

    # Two independent axes, as in TB 3.5+. ``status`` is derived, never stored.
    acknowledged = models.BooleanField(default=False)
    cleared = models.BooleanField(default=False)

    start_ts = models.DateTimeField(default=timezone.now)
    end_ts = models.DateTimeField(default=timezone.now)
    ack_ts = models.DateTimeField(null=True, blank=True)
    clear_ts = models.DateTimeField(null=True, blank=True)

    # {"message": "...", "values": {...}} — the rendered alarmDetails template
    # plus a snapshot of the values that tripped the rule.
    details = models.JSONField(null=True, blank=True)

    propagate = models.BooleanField(default=False)
    propagate_relation_types = ArrayField(models.CharField(max_length=255), default=list, blank=True)
    propagate_to_owner = models.BooleanField(default=False)
    propagate_to_tenant = models.BooleanField(default=False)
    # GRMS deviation: in TB the alarm↔entity link lives in the polymorphic
    # ``relation`` table. ``Relation`` here is device-to-device only, so the
    # propagation targets are denormalised onto the alarm and queried with GIN.
    propagate_entity_ids = ArrayField(models.UUIDField(), default=list, blank=True)

    assignee = models.ForeignKey("users.User", SET_NULL, null=True, blank=True, related_name="assigned_alarms")
    assign_ts = models.DateTimeField(null=True, blank=True)

    # Outside the TB model: bookkeeping for the notification dispatcher.
    notified_at = models.DateTimeField(null=True, blank=True)
    notified_clear_at = models.DateTimeField(null=True, blank=True)

    # TYPING
    tenant_id: UUID

    objects: ClassVar[AlarmQuerySet] = cast(AlarmQuerySet, AlarmQuerySet.as_manager())

    def __str__(self) -> str:
        return f"{self.alarm_type} ({self.severity})"

    @property
    def status(self) -> str:
        if self.cleared:
            return AlarmStatus.CLEARED_ACK if self.acknowledged else AlarmStatus.CLEARED_UNACK
        return AlarmStatus.ACTIVE_ACK if self.acknowledged else AlarmStatus.ACTIVE_UNACK

    @property
    def duration_ms(self) -> int:
        end = self.clear_ts or self.end_ts
        return int((end - self.start_ts).total_seconds() * 1000)

    class Meta(BaseModel.Meta, UpdateByModel.Meta):
        db_table = "alarms_alarm"
        ordering = ("-start_ts",)
        constraints = [
            # The deduplication mechanism, not just an invariant: the MQTT
            # disconnect topic and the watchdog both notice the same outage,
            # up to a minute apart. The second INSERT loses at the database,
            # which survives restarts in a way a Redis guard would not.
            models.UniqueConstraint(
                fields=["originator", "alarm_type"],
                condition=models.Q(cleared=False),
                name="uniq_active_alarm_per_originator_type",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "cleared", "-start_ts"], name="ix_alarm_tenant_active"),
            models.Index(fields=["originator", "-start_ts"], name="ix_alarm_originator"),
            models.Index(fields=["alarm_type", "-start_ts"], name="ix_alarm_type"),
            models.Index(fields=["severity", "-start_ts"], name="ix_alarm_severity"),
            GinIndex(fields=["propagate_entity_ids"], name="ix_alarm_propagate"),
        ]
        permissions = [
            ("ack_alarm", "Can acknowledge alarms"),
            ("clear_alarm", "Can clear alarms"),
            ("assign_alarm", "Can assign alarms"),
        ]


class AlarmComment(BaseModel):
    """
    ``SYSTEM`` entries are the lifecycle audit — severity escalation, ack, clear,
    assignment — written by the evaluator and the API, not by people.
    """

    class TYPE(models.TextChoices):
        OTHER = "OTHER", "Other"
        SYSTEM = "SYSTEM", "System"

    class SUBTYPE(models.TextChoices):
        SEVERITY_CHANGED = "SEVERITY_CHANGED", "Severity changed"
        ACKNOWLEDGED = "ACKNOWLEDGED", "Acknowledged"
        CLEARED = "CLEARED", "Cleared"
        ASSIGNED = "ASSIGNED", "Assigned"
        UNASSIGNED = "UNASSIGNED", "Unassigned"

    alarm = models.ForeignKey("alarms.Alarm", CASCADE, related_name="comments")
    user = models.ForeignKey("users.User", SET_NULL, null=True, blank=True, related_name="alarm_comments")
    alarm_comment_type = models.CharField(max_length=16, choices=TYPE.choices, default=TYPE.OTHER)
    comment = models.JSONField()

    objects: ClassVar[AlarmCommentQuerySet] = cast(AlarmCommentQuerySet, AlarmCommentQuerySet.as_manager())

    def __str__(self) -> str:
        return f"{self.alarm_comment_type} on {self.alarm.id}"

    class Meta(BaseModel.Meta):
        db_table = "alarms_alarm_comment"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["alarm", "-created_at"], name="ix_alarm_comment_alarm"),
        ]


class AlarmRuleState(BaseModel):
    """
    DURATION/REPEATING counters carried between evaluator ticks.

    GRMS deviation: TB keeps this in the rule node's heap because the rule chain
    is a long-lived actor. The GRMS evaluator is a periodic Celery task that can
    land in any worker, so the counters have to outlive the process — otherwise
    a DURATION rule would restart its clock on every deploy and never fire.

    One row per (device, alarm type), created lazily on the first match and
    deleted as soon as no rule of that type is counting.
    ``state`` maps a rule key — a severity, or ``CLEAR`` for the clear rule — to
    ``{"since": iso8601, "count": int}``.
    """

    CLEAR_KEY = "CLEAR"

    device = models.ForeignKey("main.Device", CASCADE, related_name="alarm_rule_states")
    alarm_rule_type = models.CharField(max_length=255)
    state = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)

    objects = AlarmRuleStateQuerySet.as_manager()

    def __str__(self) -> str:
        return f"{self.alarm_rule_type} @ {self.device.id}"

    class Meta(BaseModel.Meta):
        db_table = "alarms_rule_state"
        constraints = [
            models.UniqueConstraint(fields=["device", "alarm_rule_type"], name="uniq_rule_state_device_type"),
        ]
