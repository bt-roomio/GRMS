from collections import Counter
from dataclasses import dataclass

from rest_framework import serializers

from core.serializers.pagination import PaginationParams, PaginationSerializer
from main.models import Device, RoomType
from services.mapping.composite import composite_rules_issues
from services.mapping.constants import TAG_NAME_MAX_LENGTH
from services.mapping.validation import Issue, rule_errors
from services.models import Integration, Integrator, MappingProfile, MappingRule


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

    class Meta:
        model = MappingProfile
        fields = (
            "id",
            "name",
            "integrator",
            "scope",
            "room_type",
            "device",
            "integrations",
            "rules",
            "composite_rules",
            "created_at",
            "updated_at",
        )


class MappingProfileWriteSerializer(serializers.ModelSerializer):
    """The profile JSON. ``rules`` replaces all rules of the profile on save. A ``room_type`` or
    ``device`` profile names its target and applies to the integration of its integrator; a
    ``tenant`` profile has no target."""

    integrator = serializers.SlugRelatedField(slug_field="name", queryset=Integrator.objects.all())
    rules = MappingRuleSerializer(many=True)
    composite_rules = serializers.JSONField(
        required=False,
        help_text="Composite rules (see services.mapping.composite); left out of a PUT, the saved ones stay.",
    )

    class Meta:
        model = MappingProfile
        fields = ("name", "integrator", "scope", "room_type", "device", "rules", "composite_rules")

    def get_fields(self):
        fields = super().get_fields()
        if "tenant_id" in self.context:  # absent when drf-yasg builds the schema
            tenant_id = self.context["tenant_id"]
            fields["room_type"].queryset = RoomType.objects.filter(tenant_id=tenant_id)
            fields["device"].queryset = Device.objects.filter(tenant_id=tenant_id)
        return fields

    def validate_name(self, value):
        tenant_id = self.instance.tenant_id if self.instance else self.context["tenant_id"]
        duplicates = MappingProfile.objects.filter(name=value, tenant_id=tenant_id)
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
        target_field = MappingProfile.TARGET_FIELDS[scope]
        values = {field: attrs.get(field, getattr(self.instance, field, None)) for field in ("room_type", "device")}
        errors = {}
        for field in ("room_type", "device"):
            if field == target_field and values[field] is None:
                errors[field] = [f"Required for the {scope} scope."]
            elif field != target_field and values[field] is not None:
                errors[field] = [f"Must be empty for the {scope} scope."]
        if errors:
            raise serializers.ValidationError(errors)

        integrator = attrs["integrator"]
        if target_field is not None:
            tenant_id = self.instance.tenant_id if self.instance else self.context["tenant_id"]
            twins = MappingProfile.objects.filter(
                tenant_id=tenant_id, integrator=integrator, scope=scope, **{target_field: values[target_field]}
            )
            if self.instance:
                twins = twins.exclude(pk=self.instance.pk)
            if twins.exists():
                raise serializers.ValidationError({target_field: ["The integrator already has a profile for it."]})

        if self.instance is None:
            return attrs
        if self.instance.integrations.exclude(integrator=integrator).exists():
            raise serializers.ValidationError({"integrator": ["The profile is used by another integrator."]})
        if scope != MappingProfile.Scope.TENANT and self.instance.integrations.exists():
            raise serializers.ValidationError({"scope": ["The profile is used by integrations: it stays tenant."]})
        return attrs

    def create(self, validated_data):
        rules = validated_data.pop("rules")
        instance = super().create(validated_data)
        self._set_rules(instance, rules, validated_data.get("created_by"))
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
    scope: str | None
    sort_by: str


class MappingProfileFilterSerializer(PaginationSerializer[MappingProfileFilterParams]):
    SORT_CHOICES = ("name", "-name", "created_at", "-created_at")
    params_class = MappingProfileFilterParams

    search = serializers.CharField(
        default=None, allow_blank=True, help_text="Filter by name (case-insensitive substring)."
    )
    integrator = serializers.CharField(default=None, help_text="Filter by integrator name.")
    scope = serializers.ChoiceField(choices=MappingProfile.Scope.choices, default=None, help_text="Filter by scope.")
    sort_by = serializers.ChoiceField(choices=SORT_CHOICES, default="name")
