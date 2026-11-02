"""
Database side of the mapping engine: the rule an integration applies to a tag.

``TagMapper`` loads the rules of the integration's mapping profile and of the ``room_type`` and
``device`` profiles of its integrator in its tenant once, keyed by tag name. A tag takes its rule from the profile of its device,
then of its room type, then from the integration's own profile. An integration without a
profile maps nothing: values go out and come in as GRMS stores them.
"""

import logging
from collections import defaultdict
from typing import NamedTuple
from uuid import UUID

from django.db.models import Q

from services.mapping.engine import MappingError, ranges_to_external, to_external, to_grms
from services.models import Integration, MappingProfile, MappingRule

logger = logging.getLogger(__name__)


class Target(NamedTuple):
    """Where a tag lives, for picking the scoped profiles that apply to it."""

    device_id: UUID
    room_type_id: UUID | None = None


def device_target(device) -> Target:
    """The target of a device's tags. Reads ``device.room``: select it with the device."""
    room = device.room
    return Target(device.id, room.type_id if room else None)


class TagMapper:
    def __init__(self, integration=None, reload=False):
        """``reload`` reads the integration's profile from the database: a long-lived holder of
        the integration (a WebSocket connection) would otherwise miss a profile change."""
        # (scope, target id) -> {tag name: rule}; the tenant scope has no target id.
        self.rules: dict[tuple, dict[str, dict]] = defaultdict(dict)
        profile_id = getattr(integration, "mapping_profile_id", None)
        if reload and integration is not None:
            profile_id = (
                Integration.objects.filter(pk=integration.pk).values_list("mapping_profile_id", flat=True).first()
            )
        if profile_id is None:
            return
        # The scoped profiles apply only together with the integration's own profile.
        scoped = Q(
            profile__tenant_id=integration.tenant_id,
            profile__integrator_id=integration.integrator_id,
            profile__scope__in=(MappingProfile.Scope.ROOM_TYPE, MappingProfile.Scope.DEVICE),
        )
        rules = MappingRule.objects.filter(Q(profile_id=profile_id) | scoped).select_related("profile")
        for rule in rules:
            profile = rule.profile
            self.rules[(profile.scope, profile.room_type_id or profile.device_id)][rule.tag_name] = rule.as_rule()

    def rule(self, tag_name, target: Target) -> dict | None:
        """The rule of the tag name from the most specific profile that has one; ``None`` when
        no profile has a rule for it."""
        if not tag_name:
            return None
        for key in (
            (MappingProfile.Scope.DEVICE, target.device_id),
            (MappingProfile.Scope.ROOM_TYPE, target.room_type_id),
            (MappingProfile.Scope.TENANT, None),
        ):
            if (rule := self.rules.get(key, {}).get(tag_name)) is not None:
                return rule
        return None

    def tag_to_external(self, tag: dict, target: Target) -> dict:
        """The tag (with ``tag_name`` and ``tag_ranges``) with ``value`` and ``tag_ranges`` in the
        integrator's form. A stored value the rule cannot convert goes out as ``null``: the
        integrator never gets a value outside its own format."""
        rule = self.rule(tag.get("tag_name"), target)
        if rule is None:
            return tag
        try:
            tag["value"] = to_external(rule, tag.get("value"))
        except MappingError as exc:
            logger.warning(
                "Tag %s (%s): value %r not mapped: %s", tag.get("id"), rule["tag_name"], tag.get("value"), exc
            )
            tag["value"] = None
        if tag.get("tag_ranges") is not None:
            tag["tag_ranges"] = ranges_to_external(rule, tag["tag_ranges"])
        return tag

    def value_to_grms(self, value, tag_name, tag_ranges, target: Target):
        """An integrator value as the GRMS value to write, or ``SKIP``. Raises ``MappingError``."""
        rule = self.rule(tag_name, target)
        if rule is None:
            return value
        return to_grms(rule, value, tag_ranges)
