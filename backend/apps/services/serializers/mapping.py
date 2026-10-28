from dataclasses import dataclass
from uuid import UUID

from django.db.models import F

from rest_framework import serializers

from core.serializers.pagination import PaginationParams, PaginationSerializer
from main.models import Device, Room, RoomType
from services.mapping.constants import RULE_IDENTITY_FIELDS, Direction, TransformType
from services.mapping.engine import apply_overrides, normalize_number
from services.mapping.validation import rule_errors
from services.models import Integration, Integrator, MappingOverride, MappingProfile, MappingRule, TagType
from services.serializers.device_tag_types import range_allowed

# Rule fields an override may replace.
OVERRIDABLE_FIELDS = ("external", "direction", "transform", "validate", "on_invalid")


def tag_type_errors(rule: dict, tag_type: TagType, type_ranges=None) -> list[str]:
    """Checks of a rule against its tag type's ``TagRange`` values: the GRMS side of an enum and
    of a range must be values the type allows. ``type_ranges`` replaces the stored ranges."""
    if type_ranges is None:
        type_ranges = [r.range_value for r in tag_type.tag_ranges.all()]
    transform = rule.get("transform") or {}
    if transform.get("type") == TransformType.ENUM:
        unknown = [pair["grms"] for pair in transform["map"] if not range_allowed(pair["grms"], type_ranges)]
        if unknown:
            return [f"GRMS values {unknown} are not ranges of tag type {tag_type.name!r}."]
    elif transform.get("type") == TransformType.RANGE:
        grms = transform["grms"]
        bounds = f"{normalize_number(grms['min'])}-{normalize_number(grms['max'])}"
        if not range_allowed(bounds, type_ranges):
            return [f"GRMS range {bounds} is not within the ranges of tag type {tag_type.name!r}."]
    return []


def tag_type_ranges_errors(tag_type: TagType, type_ranges) -> list[str]:
    """Problems the new ``type_ranges`` of a tag type cause to the mapping rules of the type and
    to the overrides of those rules."""
    errors = []
    for rule in tag_type.mapping_rules.select_related("profile", "tag_type"):
        merged = rule.as_rule()
        errors += [
            f"Rule {rule.code!r} of profile {rule.profile.code!r}: {error}"
            for error in tag_type_errors(merged, tag_type, type_ranges)
        ]
        overrides = MappingOverride.objects.filter(
            integration__mapping_profile_id=rule.profile_id, rule_overrides__has_key=rule.code
        )
        for override in overrides:
            fields = override.rule_overrides[rule.code]
            errors += [
                f"Override {override.pk} of rule {rule.code!r}: {error}"
                for error in tag_type_errors(apply_overrides(merged, [fields]), tag_type, type_ranges)
            ]
    return errors


def override_errors(rules_by_code: dict[str, MappingRule], rule_overrides) -> list[str]:
    """Problems of an override's ``rule_overrides`` against the profile rules it changes."""
    if not isinstance(rule_overrides, dict):
        return ["rule_overrides must be an object."]
    errors = []
    for code, fields in rule_overrides.items():
        rule = rules_by_code.get(code)
        if rule is None:
            errors.append(f"Rule {code!r} is not in the integration's mapping profile.")
            continue
        if not isinstance(fields, dict):
            errors.append(f"rule_overrides.{code} must be an object.")
            continue
        if unknown := [field for field in fields if field not in OVERRIDABLE_FIELDS]:
            identity = [field for field in unknown if field in RULE_IDENTITY_FIELDS]
            errors.append(f"rule_overrides.{code} cannot change {identity or unknown}.")
            continue
        merged = apply_overrides(rule.as_rule(), [fields])
        errors += [f"{code}: {error}" for error in rule_errors(merged) or tag_type_errors(merged, rule.tag_type)]
    return errors


class TagTypeNameField(serializers.SlugRelatedField):
    """A tag type by name among the tenant's own and the shared ones; the tenant's own type wins
    when a shared type has the same name."""

    def __init__(self, **kwargs):
        super().__init__(slug_field="name", **kwargs)

    def to_internal_value(self, data):
        if not isinstance(data, str):
            self.fail("invalid")
        tag_type = self.get_queryset().filter(name=data).order_by(F("tenant_id").asc(nulls_last=True)).first()
        if tag_type is None:
            self.fail("does_not_exist", slug_name=self.slug_field, value=data)
        return tag_type


class MappingRuleSerializer(serializers.ModelSerializer):
    """A rule in its profile JSON form: ``id`` is the rule code, ``tag_type`` the name of one of the
    tenant's tag types, ``validate`` the optional limits of the external value."""

    id = serializers.CharField(source="code", max_length=100)
    tag_type = TagTypeNameField(queryset=TagType.objects.none())

    class Meta:
        model = MappingRule
        fields = ("id", "tag_type", "external", "direction", "transform", "on_invalid")

    def get_fields(self):
        fields = super().get_fields()
        # Added here, not declared: a class attribute ``validate`` would shadow Serializer.validate().
        fields["validate"] = serializers.JSONField(source="limits", required=False, allow_null=True)
        if "tenant_id" in self.context:  # absent when drf-yasg builds the schema
            fields["tag_type"].queryset = TagType.objects.available(self.context["tenant_id"]).prefetch_related(
                "tag_ranges"
            )
        return fields

    def validate(self, attrs):
        rule = MappingRule(**attrs).as_rule()  # unsaved: model defaults fill direction and on_invalid
        errors = rule_errors(rule) or tag_type_errors(rule, attrs["tag_type"])
        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class MappingProfileSerializer(serializers.ModelSerializer):
    integrator = serializers.SlugRelatedField(slug_field="name", read_only=True)
    rules = MappingRuleSerializer(many=True, read_only=True)

    class Meta:
        model = MappingProfile
        fields = ("id", "code", "name", "integrator", "schema_version", "rules", "created_at", "updated_at")


class MappingProfileWriteSerializer(serializers.ModelSerializer):
    """The profile JSON. ``rules`` replaces all rules of the profile on save."""

    integrator = serializers.SlugRelatedField(slug_field="name", queryset=Integrator.objects.all())
    rules = MappingRuleSerializer(many=True)

    class Meta:
        model = MappingProfile
        fields = ("code", "name", "integrator", "schema_version", "rules")

    def validate_code(self, value):
        tenant_id = self.instance.tenant_id if self.instance else self.context["tenant_id"]
        duplicates = MappingProfile.objects.filter(code=value, tenant_id=tenant_id)
        if self.instance:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError("A mapping profile with this code already exists.")
        return value

    def validate_rules(self, rules):
        errors = []
        for field, label in (("code", "rule ids"), ("tag_type", "tag types")):
            values = [rule[field] for rule in rules]
            if duplicates := sorted({str(value) for value in values if values.count(value) > 1}):
                errors.append(f"Duplicate {label}: {duplicates}.")
        if errors:
            raise serializers.ValidationError(errors)
        return rules

    def validate(self, attrs):
        if self.instance is None:
            return attrs
        integrations = self.instance.integrations.all()
        if integrations.exclude(integrator=attrs["integrator"]).exists():
            raise serializers.ValidationError({"integrator": ["The profile is used by another integrator."]})
        # The overrides of the integrations using the profile must still fit the new rules.
        rules_by_code = {rule["code"]: MappingRule(**rule) for rule in attrs["rules"]}
        errors = []
        for override in MappingOverride.objects.filter(integration__in=integrations):
            errors += [
                f"Override {override.pk}: {error}" for error in override_errors(rules_by_code, override.rule_overrides)
            ]
        if errors:
            raise serializers.ValidationError({"rules": errors})
        return attrs

    def create(self, validated_data):
        rules = validated_data.pop("rules")
        instance = super().create(validated_data)
        self._set_rules(instance, rules, validated_data.get("created_by"))
        return instance

    def update(self, instance, validated_data):
        rules = validated_data.pop("rules")
        instance = super().update(instance, validated_data)
        instance.rules.all().delete()
        self._set_rules(instance, rules, validated_data.get("updated_by"))
        return instance

    @staticmethod
    def _set_rules(instance, rules, user):
        MappingRule.objects.bulk_create(MappingRule(profile=instance, created_by=user, **rule) for rule in rules)


@dataclass
class MappingProfileFilterParams(PaginationParams):
    search: str | None
    integrator: str | None
    sort_by: str


class MappingProfileFilterSerializer(PaginationSerializer[MappingProfileFilterParams]):
    SORT_CHOICES = ("code", "-code", "name", "-name", "created_at", "-created_at")
    params_class = MappingProfileFilterParams

    search = serializers.CharField(
        default=None, allow_blank=True, help_text="Filter by name (case-insensitive substring)."
    )
    integrator = serializers.CharField(default=None, help_text="Filter by integrator name.")
    sort_by = serializers.ChoiceField(choices=SORT_CHOICES, default="code")


class MappingTestSerializer(serializers.Serializer):
    """Runs one rule of the profile on a value, without touching any tag."""

    rule = serializers.CharField(help_text="Rule id in the profile.")
    direction = serializers.ChoiceField(choices=(Direction.TO_EXTERNAL, Direction.TO_GRMS))
    input = serializers.JSONField(
        allow_null=True, help_text="A GRMS value for to_external, an external one for to_grms."
    )
    tag_ranges = serializers.ListField(
        child=serializers.JSONField(allow_null=True),
        default=None,
        allow_null=True,
        help_text="The tag's ranges: to_grms checks the value against them, to_external converts them.",
    )


class MappingOverrideSerializer(serializers.ModelSerializer):
    """An override of the integration's profile rules. The level's own target (``room_type``,
    ``room`` or ``device``) is required, the others must be empty; the tenant level has none."""

    class Meta:
        model = MappingOverride
        fields = (
            "id",
            "integration",
            "level",
            "room_type",
            "room",
            "device",
            "rule_overrides",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def get_fields(self):
        fields = super().get_fields()
        if "tenant_id" in self.context:  # absent when drf-yasg builds the schema
            tenant_id = self.context["tenant_id"]
            fields["integration"].queryset = Integration.objects.filter(tenant_id=tenant_id, is_active=True)
            fields["room_type"].queryset = RoomType.objects.filter(tenant_id=tenant_id)
            fields["room"].queryset = Room.objects.filter(tenant_id=tenant_id)
            fields["device"].queryset = Device.objects.filter(tenant_id=tenant_id)
        return fields

    def validate(self, attrs):
        level = attrs["level"]
        target_field = MappingOverride.TARGET_FIELDS[level]
        errors = {}
        for field in ("room_type", "room", "device"):
            if field == target_field and attrs.get(field) is None:
                errors[field] = [f"Required for the {level} level."]
            elif field != target_field and attrs.get(field) is not None:
                errors[field] = [f"Must be empty for the {level} level."]
        if errors:
            raise serializers.ValidationError(errors)

        integration = attrs["integration"]
        profile = integration.mapping_profile
        if profile is None:
            raise serializers.ValidationError({"integration": ["The integration has no mapping profile."]})
        rules = profile.rules.select_related("tag_type").prefetch_related("tag_type__tag_ranges")
        if problems := override_errors({rule.code: rule for rule in rules}, attrs.get("rule_overrides", {})):
            raise serializers.ValidationError({"rule_overrides": problems})

        target = {field: attrs.get(field) for field in ("room_type", "room", "device")}
        duplicates = MappingOverride.objects.filter(integration=integration, level=level, **target)
        if self.instance:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError("An override for this target already exists.")
        return attrs


@dataclass
class MappingOverrideFilterParams(PaginationParams):
    integration: UUID | None
    level: str | None


class MappingOverrideFilterSerializer(PaginationSerializer[MappingOverrideFilterParams]):
    params_class = MappingOverrideFilterParams

    integration = serializers.UUIDField(default=None, help_text="Filter by integration id.")
    level = serializers.ChoiceField(choices=MappingOverride.Level.choices, default=None, help_text="Filter by level.")
