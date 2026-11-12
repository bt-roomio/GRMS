from rest_framework import serializers

from services.mapping.constants import Direction


class MappingTestSerializer(serializers.Serializer):
    """A dry run of one rule. The rule is given inline (``rule`` or ``composite_rule``) or picked by
    name (``tag_name``) or id (``composite_id``) from a saved ``profile`` or as the ``integration``
    applies it (``device`` or ``room`` choose among the room type and device profiles)."""

    direction = serializers.ChoiceField(
        choices=[Direction.TO_EXTERNAL, Direction.TO_GRMS],
        help_text="to_external: GRMS -> integrator (reads); to_grms: integrator -> GRMS (writes).",
    )
    rule = serializers.JSONField(required=False, help_text="An unsaved plain rule, as in a profile's rules.")
    composite_rule = serializers.JSONField(
        required=False, help_text="An unsaved composite rule, as in a profile's composite_rules."
    )
    profile = serializers.UUIDField(required=False, help_text="A saved profile to take the rule from.")
    integration = serializers.UUIDField(
        required=False, help_text="An integration: the rule it applies, through its profile and the scoped ones."
    )
    tag_name = serializers.CharField(required=False, help_text="The plain rule of this tag name.")
    composite_id = serializers.CharField(required=False, help_text="The composite rule of this id.")
    room = serializers.UUIDField(
        required=False,
        help_text="Context: picks the effective rule for the room; for a composite rule, its live inputs "
        "(when inputs is left out) and the tags its writes would go to.",
    )
    device = serializers.UUIDField(required=False, help_text="Context: picks the effective rule for the device.")
    value = serializers.JSONField(
        required=False, help_text="The value to convert: GRMS for to_external, the integrator's for to_grms."
    )
    inputs = serializers.DictField(
        child=serializers.JSONField(allow_null=True),
        required=False,
        help_text="Composite to_external: GRMS input values by alias.",
    )
    tag_ranges = serializers.ListField(
        child=serializers.JSONField(),
        required=False,
        allow_null=True,
        help_text="Plain rule: the tag's GRMS ranges, checked on to_grms and converted on to_external.",
    )

    def validate(self, attrs):
        sources = [key for key in ("rule", "composite_rule", "profile", "integration") if key in attrs]
        if len(sources) != 1:
            raise serializers.ValidationError(
                {"non_field_errors": ["Give exactly one of rule, composite_rule, profile, integration."]}
            )
        source = sources[0]
        if source in ("profile", "integration"):
            names = [key for key in ("tag_name", "composite_id") if key in attrs]
            if len(names) != 1:
                raise serializers.ValidationError({source: ["Give exactly one of tag_name, composite_id."]})
            attrs["composite"] = names[0] == "composite_id"
        else:
            attrs["composite"] = source == "composite_rule"
        if "room" in attrs and "device" in attrs:
            raise serializers.ValidationError({"device": ["Give room or device, not both."]})

        reads = attrs["direction"] == Direction.TO_EXTERNAL
        if attrs["composite"] and reads:
            if "inputs" not in attrs and "room" not in attrs and "device" not in attrs:
                raise serializers.ValidationError({"inputs": ["Give inputs, or a room to read them from."]})
        elif "value" not in attrs:
            raise serializers.ValidationError({"value": ["This field is required."]})
        return attrs
