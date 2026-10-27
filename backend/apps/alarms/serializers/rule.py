"""
CRUD contract for alarm rules.

The body is deliberately mixed: the rule itself keeps ThingsBoard's camelCase
(``alarmType``, ``createRules``, …) so a rule exported from TB — or copied out of
docs/alarms.md — pastes in unchanged, while the GRMS envelope around it
(``device_profile``, ``enabled``) is snake_case like the rest of this API.

Nested condition trees are validated by ``DeviceProfileAlarmSerializer``, the same
validator that guarded ``profile_data["alarms"]`` before rules became rows. That
keeps one contract and one set of error paths.
"""

from rest_framework import serializers

from alarms.models import AlarmRule
from alarms.querysets.rule import AlarmRuleQuerySet
from alarms.serializers.rules import DeviceProfileAlarmSerializer
from core.utils.serializers import ValidatorSerializer
from main.models import DeviceProfile

# camelCase in the body ↔ column on the row.
RULE_FIELDS = (
    ("alarmType", "alarm_type"),
    ("createRules", "create_rules"),
    ("clearRule", "clear_rule"),
    ("propagate", "propagate"),
    ("propagateRelationTypes", "propagate_relation_types"),
    ("propagateToOwner", "propagate_to_owner"),
    ("propagateToTenant", "propagate_to_tenant"),
)

EMPTY = object()


class AlarmRuleSerializer(serializers.ModelSerializer):
    alarmType = serializers.CharField(source="alarm_type", max_length=255)
    createRules = serializers.DictField(source="create_rules")
    clearRule = serializers.JSONField(source="clear_rule", required=False, allow_null=True)
    propagateRelationTypes = serializers.ListField(
        source="propagate_relation_types",
        child=serializers.CharField(max_length=255),
        required=False,
    )
    propagateToOwner = serializers.BooleanField(source="propagate_to_owner", required=False)
    propagateToTenant = serializers.BooleanField(source="propagate_to_tenant", required=False)

    device_profile = serializers.PrimaryKeyRelatedField(queryset=DeviceProfile.objects.filter(active=True))
    device_profile_name = serializers.CharField(source="device_profile.name", read_only=True)

    class Meta:
        model = AlarmRule
        fields = (
            "id",
            "device_profile",
            "device_profile_name",
            "enabled",
            "alarmType",
            "createRules",
            "clearRule",
            "propagate",
            "propagateRelationTypes",
            "propagateToOwner",
            "propagateToTenant",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")
        # Without this DRF builds a UniqueTogetherValidator out of the model
        # constraint and reports a duplicate in ``non_field_errors``, before the
        # check in ``validate`` runs. The form needs it on ``alarmType`` to
        # highlight the field, so the explicit check owns this error.
        validators = []

    def validate_device_profile(self, value):
        tenant_id = (
            getattr(self.context.get("request").user, "tenant_id", None) if self.context.get("request") else None
        )
        if tenant_id is not None and value.tenant_id != tenant_id:
            raise serializers.ValidationError("This device profile belongs to another tenant.")
        return value

    def validate(self, attrs):
        """
        Run the whole rule through the ThingsBoard validator.

        Besides checking the condition tree, it fills in the defaults the format
        expects (``spec`` of SIMPLE, ``ignoreCase``, ``inherit``, ``timezone``),
        so what lands in the row is already normalised and the evaluator never
        meets a half-specified rule.
        """
        rule = {}
        for camel, snake in RULE_FIELDS:
            value = attrs.get(snake, EMPTY)
            if value is EMPTY:
                value = getattr(self.instance, snake, None) if self.instance else None
            if value is not None:
                rule[camel] = value

        serializer = DeviceProfileAlarmSerializer(data=rule)
        serializer.is_valid(raise_exception=True)
        cleaned = dict(serializer.validated_data)

        for camel, snake in RULE_FIELDS:
            if camel in cleaned:
                attrs[snake] = cleaned[camel]

        profile = attrs.get("device_profile") or (self.instance.device_profile if self.instance else None)
        alarm_type = attrs.get("alarm_type") or (self.instance.alarm_type if self.instance else "")
        if profile and alarm_type:
            clash = AlarmRule.objects.filter(device_profile=profile, alarm_type=alarm_type)
            if self.instance:
                clash = clash.exclude(pk=self.instance.pk)
            if clash.exists():
                # Nicer than letting the unique constraint surface as a 500.
                raise serializers.ValidationError(
                    {"alarmType": f"This profile already has a rule of type '{alarm_type}'."}
                )

        return attrs

    def create(self, validated_data):
        # The tenant follows the profile; it is never taken from the body.
        validated_data["tenant_id"] = validated_data["device_profile"].tenant_id
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if "device_profile" in validated_data:
            validated_data["tenant_id"] = validated_data["device_profile"].tenant_id
        return super().update(instance, validated_data)


class AlarmRuleFilterParams(ValidatorSerializer):
    page = serializers.IntegerField(default=1)
    size = serializers.IntegerField(default=50)
    device_profile = serializers.UUIDField(required=False)
    alarm_type = serializers.ListField(child=serializers.CharField(max_length=255), required=False)
    enabled = serializers.BooleanField(required=False, allow_null=True, default=None)
    search_value = serializers.CharField(required=False)
    sort_by = serializers.ListField(
        child=serializers.ChoiceField(choices=AlarmRuleQuerySet.SORT_FIELDS),
        required=False,
    )


class AlarmRuleBulkSerializer(ValidatorSerializer):
    """
    Replace every rule of one profile at once.

    This is the import path for a ThingsBoard profile export and the
    "save the whole editor" button: the body is exactly the array that used to
    live in ``profile_data["alarms"]``.
    """

    device_profile = serializers.PrimaryKeyRelatedField(queryset=DeviceProfile.objects.filter(active=True))
    alarms = serializers.ListField(child=serializers.DictField(), allow_empty=True)

    class Meta:
        ref_name = "AlarmRuleBulk"


class AlarmRulePreviewSerializer(ValidatorSerializer):
    """``alarms`` omitted means "dry run what is already stored for this profile"."""

    device_profile = serializers.PrimaryKeyRelatedField(queryset=DeviceProfile.objects.filter(active=True))
    alarms = serializers.ListField(child=serializers.DictField(), required=False, allow_empty=True)

    class Meta:
        ref_name = "AlarmRulePreview"


class AlarmRuleTemplateSerializer(serializers.Serializer):
    """
    Read-only catalogue for the builder's "add a typical rule" menu.

    ``rule`` is a ready ``DeviceProfileAlarm``: the front end drops it into the
    form, the operator tweaks a threshold and posts it as an ordinary rule.
    """

    id = serializers.CharField(read_only=True)
    name = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    # Keys the template leans on, to be checked against available-keys.
    requires = serializers.DictField(read_only=True)
    rule = serializers.DictField(read_only=True)

    class Meta:
        ref_name = "AlarmRuleTemplate"
