from rest_framework import serializers

from shuttle.models import AttributeKv


class TagSerializer(serializers.Serializer):
    """Unified read representation for a tag backed by either AttributeKv (attribute)
    or TsKvLatest (telemetry). Both expose ``entity_id``, the five typed value columns
    and a ``get_value`` property; they differ only in key field and timestamp field."""

    id = serializers.UUIDField(read_only=True)
    key_name = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    last_update_ts = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()

    def get_key_name(self, obj):
        return obj.attribute_key if isinstance(obj, AttributeKv) else obj.key.key

    def get_type(self, obj):
        return "ATTRIBUTE" if isinstance(obj, AttributeKv) else "TELEMETRY"

    def get_last_update_ts(self, obj):
        return obj.last_update_ts if isinstance(obj, AttributeKv) else obj.ts

    def get_value(self, obj):
        return obj.get_value


class TagUpdateSerializer(serializers.Serializer):
    """Write payload for ``PUT /tag/<id>/``. ``value`` keeps its native JSON type so the
    view can route it to the type-compatible column (bool/str/long/dbl/json)."""

    value = serializers.JSONField()

    def validate_value(self, value):
        if value is None:
            raise serializers.ValidationError("value cannot be null.")
        return value
