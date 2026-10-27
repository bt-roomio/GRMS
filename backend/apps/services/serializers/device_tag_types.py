import re

from rest_framework import serializers

from services.models import TagType
from services.serializers.tag_type import range_value_key
from shuttle.models import AttributeKv

TAG_TYPES_KEY = "TAG_TYPES"  # AttributeKv key (SERVER_SCOPE) holding a device's tag types
ATTRIBUTE = "ATTRIBUTE"
TELEMETRY = "TELEMETRY"

_NUMBER = r"\s*(-?\d+(?:\.\d+)?)\s*"
_NUMERIC_RANGE = re.compile(rf"^{_NUMBER}-{_NUMBER}$")
_NUMERIC_VALUE = re.compile(rf"^{_NUMBER}$")


def numeric_bounds(value) -> tuple[float, float] | None:
    """``(low, high)`` of a numeric range value: ``"10-50"`` is ``(10, 50)``, a number or numeric
    string is a single point (``30`` / ``"30"`` is ``(30, 30)``). ``None`` for anything else."""
    if isinstance(value, bool):  # bool is an int subclass, but not a number here
        return None
    if isinstance(value, int | float):
        return float(value), float(value)
    if isinstance(value, str):
        if match := _NUMERIC_RANGE.match(value):
            low, high = sorted(float(bound) for bound in match.groups())
            return low, high
        if match := _NUMERIC_VALUE.match(value):
            return float(match[1]), float(match[1])
    return None


def range_allowed(value, type_ranges) -> bool:
    """Whether a selected value is one of the type's range values or lies within one of its
    numeric ranges (``"10-50"`` and ``30`` are allowed by ``"0-100"``)."""
    key = range_value_key(value)
    if any(key == range_value_key(r) for r in type_ranges):
        return True
    bounds = numeric_bounds(value)
    if bounds is None:
        return False
    for r in type_ranges:
        r_bounds = numeric_bounds(r)
        if r_bounds and r_bounds[0] <= bounds[0] and bounds[1] <= r_bounds[1]:
            return True
    return False


class DeviceTagTypeListSerializer(serializers.ListSerializer):
    def validate(self, attrs):
        seen, duplicates = set(), []
        for item in attrs:
            key = (item["tag_section"], item["tag_sub_section"], item["tag_name"])
            if key in seen:
                duplicates.append(item["tag_name"])
            seen.add(key)
        if duplicates:
            raise serializers.ValidationError(f"Duplicate tags: {duplicates}.")
        return attrs


class DeviceTagTypeSerializer(serializers.Serializer):
    """One entry of a device's ``TAG_TYPES`` attribute. ``tag_sub_section`` is the attribute scope,
    required for an ``ATTRIBUTE`` tag and ignored (stored as ``null``) for a ``TELEMETRY`` one.
    ``tag_type`` is the name of one of the tenant's tag types, ``tag_ranges`` are range values of that type
    or numeric sub-ranges / values within its numeric ranges."""

    tag_section = serializers.ChoiceField(choices=(ATTRIBUTE, TELEMETRY))
    tag_sub_section = serializers.ChoiceField(
        choices=(AttributeKv.SERVER_SCOPE, AttributeKv.CLIENT_SCOPE, AttributeKv.SHARED_SCOPE), allow_null=True
    )
    tag_name = serializers.CharField()
    tag_type = serializers.SlugRelatedField(slug_field="name", queryset=TagType.objects.none())
    tag_ranges = serializers.ListField(child=serializers.JSONField(allow_null=True))

    class Meta:
        list_serializer_class = DeviceTagTypeListSerializer

    def get_fields(self):
        fields = super().get_fields()
        if "tenant_id" in self.context:  # absent when drf-yasg builds the schema
            fields["tag_type"].queryset = TagType.objects.by_tenant(self.context["tenant_id"]).prefetch_related(
                "tag_ranges"
            )
        return fields

    def to_internal_value(self, data):
        # Dropped before field validation, so any value a TELEMETRY tag carries here is accepted.
        if isinstance(data, dict) and data.get("tag_section") == TELEMETRY:
            data = {**data, "tag_sub_section": None}
        return super().to_internal_value(data)

    def validate(self, attrs):
        if attrs["tag_section"] == ATTRIBUTE and attrs["tag_sub_section"] is None:
            raise serializers.ValidationError({"tag_sub_section": ["Required for an ATTRIBUTE tag."]})
        type_ranges = [r.range_value for r in attrs["tag_type"].tag_ranges.all()]
        ranges = {range_value_key(value): value for value in attrs["tag_ranges"]}  # collapses duplicates
        unknown = [value for value in ranges.values() if not range_allowed(value, type_ranges)]
        if unknown:
            raise serializers.ValidationError({"tag_ranges": [f"Ranges do not belong to the tag type: {unknown}."]})
        return {**attrs, "tag_type": attrs["tag_type"].name, "tag_ranges": list(ranges.values())}
