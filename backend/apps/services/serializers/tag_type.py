import json
from dataclasses import dataclass
from uuid import UUID

from drf_yasg.utils import swagger_serializer_method
from rest_framework import serializers

from core.serializers.pagination import PaginationParams, PaginationSerializer
from services.models import TagRange, TagType, TagTypeGroup
from services.serializers.tag_type_group import TagTypeGroupShortSerializer, TenantUniqueNameSerializer


def _value_key(value) -> str:
    """Identity of a range value: JSON keeps types apart (``true`` vs ``1`` vs ``"1"``)."""
    return json.dumps(value, sort_keys=True)


class TagTypeSerializer(serializers.ModelSerializer):
    """Read representation: ``group`` as ``{id, name}``, ``tag_ranges`` as the list of the
    type's range values."""

    group = TagTypeGroupShortSerializer(read_only=True)
    tag_ranges = serializers.SerializerMethodField()

    class Meta:
        model = TagType
        fields = ("id", "name", "tenant", "group", "tag_ranges", "created_at", "updated_at")

    @swagger_serializer_method(serializer_or_field=serializers.ListField(child=serializers.JSONField()))
    def get_tag_ranges(self, obj):
        # Sorted in Python so a prefetched ``tag_ranges`` (list endpoint) is reused.
        ranges = sorted(obj.tag_ranges.all(), key=lambda r: (r.created_at, r.pk))
        return [r.range_value for r in ranges]


class TagTypeWriteSerializer(TenantUniqueNameSerializer):
    """Write payload. ``group`` is the id of one of the tenant's tag type groups.
    ``tag_ranges`` is a non-empty list of range values (any JSON, ``null`` included); on save
    it replaces the type's ranges, keeping those whose value is unchanged."""

    unique_name_message = "A tag type with this name already exists."
    unique_name_constraint = "unique_tag_type_name_tenant"

    group = serializers.PrimaryKeyRelatedField(queryset=TagTypeGroup.objects.none())
    tag_ranges = serializers.ListField(child=serializers.JSONField(allow_null=True), allow_empty=False)

    class Meta:
        model = TagType
        fields = ("name", "group", "tag_ranges")

    def get_fields(self):
        fields = super().get_fields()
        if "tenant_id" in self.context:  # absent when drf-yasg builds the schema
            fields["group"].queryset = TagTypeGroup.objects.by_tenant(self.context["tenant_id"])
        return fields

    def create(self, validated_data):
        tag_ranges = validated_data.pop("tag_ranges")
        instance = super().create(validated_data)
        self._set_tag_ranges(instance, tag_ranges, validated_data.get("created_by"))
        return instance

    def update(self, instance, validated_data):
        tag_ranges = validated_data.pop("tag_ranges", None)
        instance = super().update(instance, validated_data)
        if tag_ranges is not None:
            self._set_tag_ranges(instance, tag_ranges, validated_data.get("updated_by"))
        return instance

    @staticmethod
    def _set_tag_ranges(instance, values, user):
        existing = {_value_key(r.range_value): r for r in instance.tag_ranges.all()}
        ranges = {}
        for value in values:
            key = _value_key(value)
            if key not in ranges:
                ranges[key] = existing.get(key) or instance.tag_ranges.create(created_by=user, range_value=value)
        TagRange.objects.filter(pk__in=[r.pk for key, r in existing.items() if key not in ranges]).delete()


@dataclass
class TagTypeFilterParams(PaginationParams):
    search: str | None
    group: UUID | None
    sort_by: str


class TagTypeFilterSerializer(PaginationSerializer[TagTypeFilterParams]):
    SORT_CHOICES = ("name", "-name", "created_at", "-created_at")
    params_class = TagTypeFilterParams

    search = serializers.CharField(
        default=None, allow_blank=True, help_text="Filter by name (case-insensitive substring)."
    )
    group = serializers.UUIDField(default=None, help_text="Filter by tag type group id.")
    sort_by = serializers.ChoiceField(choices=SORT_CHOICES, default="name")
