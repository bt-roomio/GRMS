"""
Database side of the mapping engine: the rule an integration applies to a tag.

``TagMapper`` loads the integration's mapping profile rules (keyed by tag type name) and its
overrides once, then resolves the rule of a device's tag with the overrides applied from the
least specific level (tenant) to the most specific one (device). An integration without a
profile maps nothing: values go out and come in as GRMS stores them.
"""

import logging
from typing import NamedTuple
from uuid import UUID

from services.mapping.engine import MappingError, apply_overrides, ranges_to_external, to_external, to_grms
from services.models import Integration, MappingOverride, MappingRule

logger = logging.getLogger(__name__)


class Target(NamedTuple):
    """Where a tag lives, for picking the overrides of each level."""

    device_id: UUID
    room_id: UUID | None = None
    room_type_id: UUID | None = None


def device_target(device) -> Target:
    """The target of a device's tags. Reads ``device.room``: select it with the device."""
    room = device.room
    return Target(device.id, device.room_id, room.type_id if room else None)


class TagMapper:
    def __init__(self, integration=None, reload=False):
        """``reload`` reads the integration's profile from the database: a long-lived holder of
        the integration (a WebSocket connection) would otherwise miss a profile change."""
        self.rules: dict[str, dict] = {}
        self.overrides: dict[tuple, dict] = {}
        profile_id = getattr(integration, "mapping_profile_id", None)
        if reload and integration is not None:
            profile_id = (
                Integration.objects.filter(pk=integration.pk).values_list("mapping_profile_id", flat=True).first()
            )
        if profile_id is None:
            return
        rules = MappingRule.objects.filter(profile_id=profile_id).select_related("tag_type")
        # A tenant's own type and a shared one may have the same name: the own type's rule wins.
        rules = sorted(rules, key=lambda rule: rule.tag_type.tenant_id is not None)
        self.rules = {rule.tag_type.name: rule.as_rule() for rule in rules}
        for override in MappingOverride.objects.filter(integration=integration):
            target_id = override.room_type_id or override.room_id or override.device_id
            self.overrides[(override.level, target_id)] = override.rule_overrides

    def rule(self, tag_type, target: Target) -> dict | None:
        """The rule of the tag type with the target's overrides applied; ``None`` when the
        profile has no rule for it."""
        rule = self.rules.get(tag_type) if tag_type else None
        if rule is None:
            return None
        levels = (
            (MappingOverride.Level.TENANT, None),
            (MappingOverride.Level.ROOM_TYPE, target.room_type_id),
            (MappingOverride.Level.ROOM, target.room_id),
            (MappingOverride.Level.DEVICE, target.device_id),
        )
        overrides = [
            self.overrides.get((level, target_id), {}).get(rule["id"])
            for level, target_id in levels
            if level == MappingOverride.Level.TENANT or target_id is not None
        ]
        return apply_overrides(rule, overrides)

    def tag_to_external(self, tag: dict, target: Target) -> dict:
        """The tag (with ``tag_type`` and ``tag_ranges``) with ``value`` and ``tag_ranges`` in the
        integrator's form. A stored value the rule cannot convert goes out as ``null``: the
        integrator never gets a value outside its own format."""
        rule = self.rule(tag.get("tag_type"), target)
        if rule is None:
            return tag
        try:
            tag["value"] = to_external(rule, tag.get("value"))
        except MappingError as exc:
            logger.warning(
                "Tag %s: value %r not mapped by rule %s: %s", tag.get("id"), tag.get("value"), rule["id"], exc
            )
            tag["value"] = None
        if tag.get("tag_ranges") is not None:
            tag["tag_ranges"] = ranges_to_external(rule, tag["tag_ranges"])
        return tag

    def value_to_grms(self, value, tag_type, tag_ranges, target: Target):
        """An integrator value as the GRMS value to write, or ``SKIP``. Raises ``MappingError``."""
        rule = self.rule(tag_type, target)
        if rule is None:
            return value
        return to_grms(rule, value, tag_ranges)
