"""
Database side of the mapping engine: the rule an integration applies to a tag.

``TagMapper`` loads the rules of the integration's mapping profile and of the ``room_type`` and
``device`` profiles of its integrator in its tenant once, keyed by tag name. A tag takes its rule
from the profile of its device, then of its room type, then from the integration's own profile.
Composite rules follow the same order by their id. An integration without a profile maps
nothing: values go out and come in as GRMS stores them.
"""

import logging
from collections import defaultdict
from collections.abc import Iterable
from typing import NamedTuple
from uuid import UUID

from django.db.models import Q

from services.mapping.engine import MappingError, ranges_to_external, to_external, to_grms
from services.models import Integration, MappingProfile, MappingRule

logger = logging.getLogger(__name__)


class Target(NamedTuple):
    """Where a tag lives, for picking the scoped profiles that apply to it."""

    device_id: UUID | None  # None: no device in particular, only the room type and tenant profiles apply
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
        # (scope, target id) -> {composite rule id: composite rule}
        self.composites: dict[tuple, dict[str, dict]] = defaultdict(dict)
        profile_id = getattr(integration, "mapping_profile_id", None)
        if reload and integration is not None:
            profile_id = (
                Integration.objects.filter(pk=integration.pk).values_list("mapping_profile_id", flat=True).first()
            )
        if profile_id is None or integration is None:
            return
        # The scoped profiles apply only together with the integration's own profile.
        scoped = Q(
            profile__tenant_id=integration.tenant_id,
            profile__integrator_id=integration.integrator_id,
            profile__scope__in=(MappingProfile.Scope.ROOM_TYPE, MappingProfile.Scope.DEVICE),
        )
        rules = MappingRule.objects.filter(Q(profile_id=profile_id) | scoped).select_related("profile")
        profiles = MappingProfile.objects.filter(
            Q(pk=profile_id)
            | Q(
                tenant_id=integration.tenant_id,
                integrator_id=integration.integrator_id,
                scope__in=(MappingProfile.Scope.ROOM_TYPE, MappingProfile.Scope.DEVICE),
            )
        ).exclude(composite_rules=[])
        for scope, room_type_id, device_id, composite_rules in profiles.values_list(
            "scope", "room_type_id", "device_id", "composite_rules"
        ):
            self.composites[(scope, room_type_id or device_id)] = {rule["id"]: rule for rule in composite_rules}
        for rule in rules:
            profile = rule.profile
            by_name = self.rules[(profile.scope, profile.room_type_id or profile.device_id)]
            as_rule = rule.as_rule()
            for tag_name in rule.tag_names:
                if tag_name in by_name:  # the serializer forbids it; rows written past it may still have it
                    logger.warning(
                        "Mapping profile %s has several rules for tag %r: the last one applies.", profile.pk, tag_name
                    )
                by_name[tag_name] = as_rule

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

    @property
    def composite_outputs(self) -> set[str]:
        """The output tag names of every composite rule the mapper may apply."""
        return {rule["output"]["tag_name"] for rules in self.composites.values() for rule in rules.values()}

    def composites_for_room(self, room_type_id, device_ids: Iterable[UUID]) -> list[tuple[dict, UUID | None]]:
        """The composite rules of a room as ``(rule, device id)``: a device profile's rule reads its
        inputs from that device only (``None`` for the room type and tenant ones, which read them
        from the whole room). A rule replaces the less specific ones with its ``id`` or its output
        tag name, so one output name has one rule in a room; between devices the first one (by
        device id) keeps it."""
        chosen: dict[str, tuple[dict, UUID | None]] = {}  # output tag name -> (rule, device id)

        def choose(rule, device_id):
            name = rule["output"]["tag_name"]
            for other_name, (other, _) in list(chosen.items()):
                if other["id"] == rule["id"] and other_name != name:
                    del chosen[other_name]  # the rule of this id now makes another output
            chosen[name] = (rule, device_id)

        for key in ((MappingProfile.Scope.TENANT, None), (MappingProfile.Scope.ROOM_TYPE, room_type_id)):
            for rule in self.composites.get(key, {}).values():
                choose(rule, None)
        bound: dict[str, UUID] = {}  # output tag name or rule id -> the device that has it
        for device_id in sorted(device_ids, key=str):
            for rule in self.composites.get((MappingProfile.Scope.DEVICE, device_id), {}).values():
                claims = (f"id:{rule['id']}", f"output:{rule['output']['tag_name']}")
                if taken := next((bound[claim] for claim in claims if claim in bound), None):
                    logger.warning(
                        "Composite rule %r of device %s clashes with one of device %s in the same room: "
                        "the first one applies.",
                        rule["id"],
                        device_id,
                        taken,
                    )
                    continue
                bound.update(dict.fromkeys(claims, device_id))
                choose(rule, device_id)
        return list(chosen.values())

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
                "Tag %s (%s): value %r not mapped: %s", tag.get("id"), tag.get("tag_name"), tag.get("value"), exc
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
        return to_grms(rule, value, tag_ranges, tag_name)
