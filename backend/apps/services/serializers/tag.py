from datetime import datetime

from rest_framework import serializers

from core.utils.date import unix_to_datetime
from services.utils.values import get_non_null_value
from shuttle.models import AttributeKv


class UnixMsDateTimeField(serializers.DateTimeField):
    """Renders the Unix-millisecond timestamps stored by AttributeKv (``last_update_ts``)
    and TsKvLatest (``ts``) as an ISO 8601 datetime, so API consumers never see the raw
    epoch value."""

    def to_representation(self, value):
        if value is not None and not isinstance(value, datetime):
            value = unix_to_datetime(value)
        return super().to_representation(value)


class _RoomTagSerializer(serializers.Serializer):
    """Projects an AttributeKv/TsKvLatest ``.values()`` row from the room querysets to the
    unified tag shape ``{id, key_name, value, updated_at}`` — the same shape the ``tag``
    detail stream returns. Subclasses bind the key and timestamp columns."""

    id = serializers.UUIDField()
    value = serializers.SerializerMethodField()

    def get_value(self, dictionary):
        return get_non_null_value(dictionary)


class RoomAttributeTagSerializer(_RoomTagSerializer):
    key_name = serializers.CharField(source="attribute_key")
    updated_at = UnixMsDateTimeField(source="last_update_ts")


class RoomTelemetryTagSerializer(_RoomTagSerializer):
    key_name = serializers.CharField(source="key__key")
    updated_at = UnixMsDateTimeField(source="ts")


class TagUpdatedAtField(UnixMsDateTimeField):
    """Picks the timestamp column of whichever model backs the tag: AttributeKv keeps it in
    ``last_update_ts``, TsKvLatest in ``ts``."""

    def to_representation(self, value):
        ts = value.last_update_ts if isinstance(value, AttributeKv) else value.ts
        return super().to_representation(ts)


class TagSerializer(serializers.Serializer):
    """Unified read representation for a tag backed by either AttributeKv (attribute)
    or TsKvLatest (telemetry). Both expose ``entity_id``, the five typed value columns
    and a ``get_value`` property; they differ only in key and timestamp fields."""

    id = serializers.UUIDField(read_only=True)
    key_name = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()
    updated_at = TagUpdatedAtField(source="*", read_only=True)

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
