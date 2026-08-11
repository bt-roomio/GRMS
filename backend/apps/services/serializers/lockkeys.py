from rest_framework import serializers

from main.models import PublicSpace, Room


class RoomLockKeySerializer(serializers.ModelSerializer):
    space_id = serializers.UUIDField(source="effective_device_id")
    space_type = serializers.SerializerMethodField()
    space_name = serializers.CharField(source="number")
    is_online = serializers.BooleanField(source="effective_device_status")

    def get_space_type(self, _):
        return "Room"

    class Meta:
        model = Room
        fields = ("space_id", "space_type", "space_name", "is_online")


class PublicSpaceLockKeySerializer(serializers.ModelSerializer):
    space_id = serializers.UUIDField(source="effective_device_id")
    space_type = serializers.SerializerMethodField()
    space_name = serializers.CharField(source="name")
    is_online = serializers.BooleanField(source="effective_device_status")

    def get_space_type(self, _):
        return "PublicSpace"

    class Meta:
        model = PublicSpace
        fields = ("space_id", "space_type", "space_name", "is_online")


class LockKeyOpenResponseSerializer(serializers.Serializer):
    space_id = serializers.CharField()
    statusCode = serializers.CharField()
    openingSuccess = serializers.BooleanField()
