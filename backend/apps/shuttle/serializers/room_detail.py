from rest_framework import serializers

from core.utils.serializers import ValidatorSerializer
from shuttle.constants import STATIC_KEYS


class RoomDetailWsFilterBodySerializer(ValidatorSerializer):
    pk = serializers.UUIDField(required=True, help_text="Room ID")
    keys = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="List of keys to filter the room details",
        default=STATIC_KEYS,
    )

    def validate_keys(self, value):
        """
        Ensures that STATIC_KEYS are always included in the keys.
        """
        if not value:
            value = []
        return list(set(value + STATIC_KEYS))
