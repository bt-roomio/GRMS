from rest_framework import serializers

from services.utils.values import get_non_null_value
from shuttle.models import AttributeKv


class _RoomTagSerializer(serializers.Serializer):
    """Projects an AttributeKv/TsKvLatest ``.values()`` row from the room querysets to the
    unified tag shape ``{id, key_name, value}`` — the same shape the ``tag`` detail stream
    returns. Subclasses bind the key column."""

    id = serializers.UUIDField()
    value = serializers.SerializerMethodField()

    def get_value(self, obj):
        return get_non_null_value(obj)


class RoomAttributeTagSerializer(_RoomTagSerializer):
    key_name = serializers.CharField(source="attribute_key")


class RoomTelemetryTagSerializer(_RoomTagSerializer):
    key_name = serializers.CharField(source="key__key")


class TagSerializer(serializers.Serializer):
    """Unified read representation for a tag backed by either AttributeKv (attribute)
    or TsKvLatest (telemetry). Both expose ``entity_id``, the five typed value columns
    and a ``get_value`` property; they differ only in key field."""

    id = serializers.UUIDField(read_only=True)
    key_name = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()

    def get_key_name(self, obj):
        return obj.attribute_key if isinstance(obj, AttributeKv) else obj.key.key

    def get_value(self, dictionary):
        return dictionary.get_value


class TagUpdateSerializer(serializers.Serializer):
    """Write payload for ``PUT /tag/<id>/``. ``value`` keeps its native JSON type so the
    view can route it to the type-compatible column (bool/str/long/dbl/json)."""

    value = serializers.JSONField()

    def validate_value(self, value):
        if value is None:
            raise serializers.ValidationError("value cannot be null.")
        return value
