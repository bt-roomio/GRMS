from collections import Counter
from dataclasses import dataclass
from uuid import UUID

from django.db import IntegrityError

from rest_framework import serializers

from core.serializers.pagination import PaginationParams, PaginationSerializer
from main.models import Device, RoomType
from services.mapping.composite import composite_rules_issues
from services.mapping.constants import TAG_NAME_MAX_LENGTH
from services.mapping.validation import Issue, rule_errors
from services.models import SCOPE_TARGETS, Integration, Integrator, MappingProfile, MappingRule, ScopeTarget

# The constraints a concurrent save may break past the checks: constraint name -> (field, message).
RACE_ERRORS = {
    "unique_mapping_profile_name_tenant": ("name", "A mapping profile with this name already exists."),
    **{
        target.constraint: (target.field, "Another profile of the integrator has just taken one of these targets.")
        for target in SCOPE_TARGETS.values()
    },
}


def race_error(exc: IntegrityError) -> serializers.ValidationError:
    """The 400 for a uniqueness constraint another save broke between the checks and the write;
    re-raises any other integrity error."""
    constraint = getattr(getattr(exc.__cause__, "diag", None), "constraint_name", None)
    if constraint not in RACE_ERRORS:
        raise exc
    field, message = RACE_ERRORS[constraint]
    return serializers.ValidationError({field: [message]})


class MappingRuleSerializer(serializers.ModelSerializer):
    """A rule in its profile JSON form: ``tag_names`` are the attribute or telemetry keys of the
    tags it converts, ``on_invalid_value`` the GRMS value written instead of an invalid one under
    ``on_invalid: const``."""

    tag_names = serializers.ListField(child=serializers.CharField(max_length=TAG_NAME_MAX_LENGTH), allow_empty=False)

    class Meta:
        model = MappingRule
        fields = ("tag_names", "external", "direction", "transform", "on_invalid", "on_invalid_value")

    def validate(self, attrs):
        rule = MappingRule(**attrs).as_rule()  # unsaved: model defaults fill direction and on_invalid
        if errors := rule_errors(rule):
            raise serializers.ValidationError(errors)
        return attrs


def issues_by_field(issues: list[Issue]) -> dict[str, list[str]]:
    """Issues as a DRF error dict: the field path (``conditions[1].when.mode``) -> its messages;
    issues of the whole rule go under ``non_field_errors``."""
    errors: dict[str, list[str]] = {}
    for issue in issues:
        errors.setdefault(issue.field or "non_field_errors", []).append(issue.message)
    return errors


class MappingProfileSerializer(serializers.ModelSerializer):
    integrator = serializers.SlugRelatedField(slug_field="name", read_only=True)
    rules = MappingRuleSerializer(many=True, read_only=True)
    integrations = serializers.PrimaryKeyRelatedField(
        many=True, read_only=True, help_text="Integrations using the profile as their mapping_profile."
    )
    room_types = serializers.PrimaryKeyRelatedField(
        many=True, read_only=True, help_text="The room types of a room_type profile."
    )
    devices = serializers.PrimaryKeyRelatedField(
        many=True, read_only=True, help_text="The devices of a device profile."
    )

    class Meta:
        model = MappingProfile
        fields = (
            "id",
            "name",
            "integrator",
            "scope",
            "room_types",
            "devices",
            "integrations",
            "rules",
            "composite_rules",
            "created_at",
            "updated_at",
        )


class MappingProfileWriteSerializer(serializers.ModelSerializer):
    """The profile JSON. ``rules`` replaces all rules of the profile on save. A ``room_type`` or
    ``device`` profile names its targets (``room_types`` or ``devices``) and applies to the
    integration of its integrator; a ``tenant`` profile has none."""

    integrator = serializers.SlugRelatedField(slug_field="name", queryset=Integrator.objects.all())
    room_types = serializers.PrimaryKeyRelatedField(
        many=True,
        required=False,
        queryset=RoomType.objects.none(),
        help_text="The room types of a room_type profile; left out of a PUT, the saved ones stay.",
    )
    devices = serializers.PrimaryKeyRelatedField(
        many=True,
        required=False,
        queryset=Device.objects.none(),
        help_text="The devices of a device profile; left out of a PUT, the saved ones stay.",
    )
    rules = MappingRuleSerializer(many=True)
    composite_rules = serializers.JSONField(
        required=False,
        help_text="Composite rules (see services.mapping.composite); left out of a PUT, the saved ones stay.",
    )

    class Meta:
        model = MappingProfile
        fields = ("name", "integrator", "scope", "room_types", "devices", "rules", "composite_rules")

    def get_fields(self):
        fields = super().get_fields()
        if "tenant_id" in self.context:  # absent when drf-yasg builds the schema
            tenant_id = self.context["tenant_id"]
            fields["room_types"].child_relation.queryset = RoomType.objects.filter(tenant_id=tenant_id)
            fields["devices"].child_relation.queryset = Device.objects.filter(tenant_id=tenant_id)
        return fields

    @property
    def tenant_id(self):
        return self.instance.tenant_id if self.instance else self.context["tenant_id"]

    def validate_name(self, value):
        duplicates = MappingProfile.objects.filter(name=value, tenant_id=self.tenant_id)
        if self.instance:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError("A mapping profile with this name already exists.")
        return value

    def validate_rules(self, rules):
        # A tag takes its rule by name, so a name belongs to one rule of the profile.
        counts = Counter(name for rule in rules for name in rule["tag_names"])
        if duplicates := sorted(name for name, count in counts.items() if count > 1):
            raise serializers.ValidationError([f"Duplicate tag names: {duplicates}."])
        return rules

    def _validate_composite_rules(self, attrs):
        composite_rules = attrs.get("composite_rules", getattr(self.instance, "composite_rules", []))
        plain_tag_names = {name for rule in attrs["rules"] for name in rule["tag_names"]}
        per_rule, general = composite_rules_issues(composite_rules, plain_tag_names)
        if general:
            raise serializers.ValidationError({"composite_rules": [issue.message for issue in general]})
        if any(per_rule):
            raise serializers.ValidationError({"composite_rules": [issues_by_field(issues) for issues in per_rule]})

    def validate(self, attrs):
        self._validate_composite_rules(attrs)
        # A field left out of the body keeps the saved value (none for a new profile).
        scope = attrs.get("scope", getattr(self.instance, "scope", MappingProfile.Scope.TENANT))
        own = SCOPE_TARGETS.get(scope)
        errors = {}
        for target in SCOPE_TARGETS.values():
            given = attrs.pop(target.field, None)
            if target is not own:
                if given:  # the targets of the scope the profile leaves go with the save
                    errors[target.field] = [f"Must be empty for the {scope} scope."]
                continue
            if given is not None:
                target_ids = list(dict.fromkeys(item.pk for item in given))  # a target named twice is one
            elif self.instance is not None and self.instance.scope == scope:
                target_ids = list(target.link.objects.filter(profile=self.instance).values_list(target.key, flat=True))
            else:
                target_ids = []
            if not target_ids:
                errors[target.field] = [f"Required for the {scope} scope."]
            attrs["target_ids"] = target_ids
        if errors:
            raise serializers.ValidationError(errors)

        integrator = attrs["integrator"]
        if own is not None and (taken := self._taken_targets(own, attrs["target_ids"], integrator)):
            raise serializers.ValidationError({own.field: taken})

        if self.instance is None:
            return attrs
        if self.instance.integrations.exclude(integrator=integrator).exists():
            raise serializers.ValidationError({"integrator": ["The profile is used by another integrator."]})
        if scope != MappingProfile.Scope.TENANT and self.instance.integrations.exists():
            raise serializers.ValidationError({"scope": ["The profile is used by integrations: it stays tenant."]})
        return attrs

    def _taken_targets(self, target: ScopeTarget, target_ids, integrator) -> list[str]:
        """Errors for the targets another profile of the integrator in the tenant already has."""
        taken = target.link.objects.filter(
            profile__tenant_id=self.tenant_id, profile__integrator=integrator, **{f"{target.key}__in": target_ids}
        ).select_related("profile")
        if self.instance:
            taken = taken.exclude(profile=self.instance)
        return [
            f"{target.label} {getattr(link, f'{target.key}_id')} already belongs to the integrator's profile "
            f"{link.profile.name!r}."
            for link in taken.order_by(target.key)
        ]

    def create(self, validated_data):
        rules = validated_data.pop("rules")
        target_ids = validated_data.pop("target_ids", [])
        instance = super().create(validated_data)
        self._set_rules(instance, rules, validated_data.get("created_by"))
        self._set_targets(instance, target_ids, validated_data.get("created_by"), None)
        if instance.scope == MappingProfile.Scope.TENANT:
            # The first profile goes live on the integration; switching to another one stays explicit.
            Integration.objects.filter(
                tenant_id=instance.tenant_id,
                integrator_id=instance.integrator_id,
                is_active=True,
                mapping_profile__isnull=True,
            ).update(mapping_profile=instance)
        return instance

    def update(self, instance, validated_data):
        rules = validated_data.pop("rules")
        target_ids = validated_data.pop("target_ids", [])
        previous = MappingProfile(scope=instance.scope, integrator_id=instance.integrator_id)
        instance = super().update(instance, validated_data)
        instance.rules.all().delete()
        self._set_rules(instance, rules, validated_data.get("updated_by"))
        self._set_targets(instance, target_ids, validated_data.get("updated_by"), previous)
        return instance

    @staticmethod
    def _set_rules(instance, rules, user):
        MappingRule.objects.bulk_create(MappingRule(profile=instance, created_by=user, **rule) for rule in rules)

    @staticmethod
    def _set_targets(instance, target_ids, user, previous):
        """Brings the links of the profile to ``target_ids``, touching only the ones that change;
        ``previous`` holds the scope and integrator before the save (``None`` for a new profile)."""
        if previous is not None and previous.scope != instance.scope and (left := SCOPE_TARGETS.get(previous.scope)):
            left.link.objects.filter(profile=instance).delete()
        own = SCOPE_TARGETS.get(instance.scope)
        if own is None:
            return
        links = own.link.objects.filter(profile=instance)
        kept = set()
        if previous is not None and previous.scope == instance.scope:
            links.exclude(**{f"{own.key}__in": target_ids}).delete()
            if previous.integrator_id != instance.integrator_id:
                links.update(integrator_id=instance.integrator_id)
            kept = set(links.values_list(own.key, flat=True))
        own.link.objects.bulk_create(
            own.link(
                profile=instance,
                tenant_id=instance.tenant_id,
                integrator_id=instance.integrator_id,
                created_by=user,
                **{f"{own.key}_id": target_id},
            )
            for target_id in target_ids
            if target_id not in kept
        )


@dataclass
class MappingProfileFilterParams(PaginationParams):
    search: str | None
    integrator: str | None
    scope: str | None
    room_type: UUID | None
    device: UUID | None
    sort_by: str


class MappingProfileFilterSerializer(PaginationSerializer[MappingProfileFilterParams]):
    SORT_CHOICES = ("name", "-name", "created_at", "-created_at")
    params_class = MappingProfileFilterParams

    search = serializers.CharField(
        default=None, allow_blank=True, help_text="Filter by name (case-insensitive substring)."
    )
    integrator = serializers.CharField(default=None, help_text="Filter by integrator name.")
    scope = serializers.ChoiceField(choices=MappingProfile.Scope.choices, default=None, help_text="Filter by scope.")
    room_type = serializers.UUIDField(default=None, help_text="Only the room_type profile of this room type.")
    device = serializers.UUIDField(default=None, help_text="Only the device profile of this device.")
    sort_by = serializers.ChoiceField(choices=SORT_CHOICES, default="name")
