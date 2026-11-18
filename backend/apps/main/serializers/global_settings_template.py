from typing import ClassVar
from uuid import UUID

from django.utils import timezone

from drf_yasg.utils import swagger_serializer_method
from rest_framework import serializers

from core.utils.serializers import ValidatorSerializer
from main.models import GlobalSettingsTemplate, Room


class GlobalSettingsTemplateFilterParams(ValidatorSerializer):
    sort_by = serializers.ListField(
        child=serializers.ChoiceField(
            choices=["-created_at", "created_at", "name", "-name", "used", "-used"],
            default="-created_at",
        ),
        required=False,
    )
    search_field = serializers.ChoiceField(choices=("name",), required=False)
    search_value = serializers.CharField(required=False)
    page = serializers.IntegerField(default=1, min_value=1)
    size = serializers.IntegerField(default=50, min_value=1, max_value=200)


class GlobalSettingsTemplateSerializer(serializers.ModelSerializer):
    config = serializers.JSONField(required=False)

    def validate_name(self, value):
        value = value.strip()
        query = GlobalSettingsTemplate.objects.filter(tenant=self.context["tenant"], name__iexact=value)
        if self.instance is not None:
            query = query.exclude(pk=self.instance.pk)
        if query.exists():
            raise serializers.ValidationError(f"Global settings template with name '{value}' already exists.")
        return value

    def validate_config(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Config must be a JSON object.")
        return value

    def update(self, instance, validated_data):
        if "config" in validated_data and validated_data["config"] != instance.config:
            validated_data["config_updated_at"] = timezone.now()
        return super().update(instance, validated_data)

    class Meta:
        model = GlobalSettingsTemplate
        fields = ("id", "name", "config", "used", "config_updated_at", "created_at", "updated_at")
        read_only_fields = ("used", "config_updated_at")


class GlobalSettingsRoomFilterParams(ValidatorSerializer):
    """
    Query params:
    - ``room_types=<id1>,<id2>`` (repeating the param works too);
    - ``blocks=<block>:<floor>,<floor>``, repeated per rule (``blocks=1:1,2,3&blocks=2:5``).
      A block without floors (``blocks=2``) selects the whole block, floors without a block
      (``blocks=:1,2``) select those floors in every block. Rules are combined with OR;
    - ``search_field`` + ``search_value``: case-insensitive substring search by room number,
      floor, block, room type title or the name of the shown device.
    """

    # search_field -> RoomQuerySet.global_settings lookup
    SEARCH_FIELD_MAP: ClassVar = {
        "number": "number",
        "floor": "floor",
        "block": "block",
        "room_type": "type__title",
        "device": "device_name",
    }

    room_types = serializers.ListField(child=serializers.CharField(), required=False)
    blocks = serializers.ListField(child=serializers.CharField(), required=False)
    search_field = serializers.ChoiceField(choices=tuple(SEARCH_FIELD_MAP), required=False)
    search_value = serializers.CharField(required=False)

    def validate(self, attrs):
        if "search_field" in attrs and "search_value" not in attrs:
            raise serializers.ValidationError({"search_value": "search_value is required with search_field."})
        if "search_value" in attrs and "search_field" not in attrs:
            raise serializers.ValidationError({"search_field": "search_field is required with search_value."})
        if "search_field" in attrs:
            attrs["search_field"] = self.SEARCH_FIELD_MAP[attrs["search_field"]]
        return attrs

    def validate_room_types(self, value):
        ids = [item.strip() for raw in value for item in raw.split(",") if item.strip()]
        return serializers.ListField(child=serializers.UUIDField()).run_validation(ids)

    def validate_blocks(self, value):
        """Returns ``{block: floors}``; the ``None`` block means any block, empty floors mean all floors."""
        blocks: dict[str | None, list[str]] = {}
        for raw in value:
            block, _, floors = raw.partition(":")
            block = block.strip() or None
            floors = [floor.strip() for floor in floors.split(",") if floor.strip()]
            if block is None and not floors:
                raise serializers.ValidationError(
                    f"Invalid blocks rule '{raw}', expected <block>, <block>:<floor>,<floor> or :<floor>,<floor>."
                )
            if block in blocks and (not blocks[block] or not floors):
                blocks[block] = []  # the whole block wins over a floor subset
            else:
                blocks.setdefault(block, []).extend(floors)
        return blocks


class GlobalSettingsRoomFilterParamsSwagger(serializers.Serializer):
    """Swagger-only description of GlobalSettingsRoomFilterParams."""

    room_types = serializers.CharField(required=False, help_text="Comma-separated room type ids: id1,id2")
    blocks = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text=(
            "Repeated per rule, rules are combined with OR: <block>:<floor>,<floor> (e.g. 1:1,2,3). "
            "A block without floors selects all of it, :<floor>,<floor> selects the floors in every block."
        ),
    )
    search_field = serializers.ChoiceField(
        choices=tuple(GlobalSettingsRoomFilterParams.SEARCH_FIELD_MAP), required=False
    )
    search_value = serializers.CharField(required=False, help_text="Case-insensitive substring, needs search_field.")


class GlobalSettingsRoomTemplateSerializer(serializers.Serializer):
    """Swagger-only description of ``GlobalSettingsRoomSerializer.template``."""

    id = serializers.UUIDField()
    name = serializers.CharField(allow_null=True)
    status = serializers.ChoiceField(choices=GlobalSettingsTemplate.STATUSES)


class GlobalSettingsRoomSerializer(serializers.Serializer):
    """
    Serializes the dict rows of ``RoomQuerySet.global_settings``; pass the rows' templates
    as ``context["templates"]`` (see ``templates_of_rows``).
    """

    id = serializers.UUIDField()
    number = serializers.CharField()
    floor = serializers.CharField()
    block = serializers.CharField()
    room_type = serializers.SerializerMethodField()
    device = serializers.JSONField()
    template = serializers.SerializerMethodField()

    def get_room_type(self, row):
        if row["type_id"] is None:
            return None
        return {"id": row["type_id"], "title": row["type__title"]}

    @staticmethod
    def templates_of_rows(rows, tenant) -> dict[str, GlobalSettingsTemplate]:
        """The tenant's templates referenced by the rows' SERVER_SCOPE ``template_id``, by id."""
        ids = set()
        for row in rows:
            try:
                ids.add(UUID(str((row["applied_template"] or {}).get("id"))))
            except ValueError:
                continue
        templates = GlobalSettingsTemplate.objects.filter(tenant=tenant, id__in=ids).only(
            "id", "name", "config_updated_at"
        )
        return {str(template.id): template for template in templates}

    @swagger_serializer_method(serializer_or_field=GlobalSettingsRoomTemplateSerializer(allow_null=True))
    def get_template(self, row):
        applied = row["applied_template"]
        if not applied or not applied.get("id"):
            return None
        template = self.context["templates"].get(applied["id"])
        if template is None:
            return {"id": applied["id"], "name": None, "status": GlobalSettingsTemplate.DELETED}
        outdated = template.config_updated_at.timestamp() * 1000 > applied["ts"]
        status = GlobalSettingsTemplate.OUTDATED if outdated else GlobalSettingsTemplate.UP_TO_DATE
        return {"id": template.id, "name": template.name, "status": status}


class ApplyGlobalSettingsTemplateSerializer(ValidatorSerializer):
    room_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)
    template_id = serializers.UUIDField()

    def validate_room_ids(self, value):
        room_ids = list(dict.fromkeys(value))
        found = set(
            Room.objects.filter(id__in=room_ids, tenant=self.context["tenant"], active=True).values_list(
                "id", flat=True
            )
        )
        missing = [str(room_id) for room_id in room_ids if room_id not in found]
        if missing:
            raise serializers.ValidationError(f"Rooms not found: {', '.join(missing)}.")
        return room_ids

    def validate_template_id(self, value):
        template = GlobalSettingsTemplate.objects.filter(pk=value, tenant=self.context["tenant"]).first()
        if template is None:
            raise serializers.ValidationError("Global settings template not found.")
        return template


class ApplyGlobalSettingsTemplateResponseSerializer(serializers.Serializer):
    devices = serializers.ListField(child=serializers.UUIDField())
