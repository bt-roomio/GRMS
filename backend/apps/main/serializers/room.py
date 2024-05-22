from django.utils import choices
from rest_framework import serializers

from core.utils.serializers import ValidatorSerializer
from main.models import Room, Tenant
from main.serializers.device import DeviceSerializer


class RoomSerializer(serializers.ModelSerializer):
    tenant = serializers.PrimaryKeyRelatedField(queryset=Tenant.objects.all(), required=False)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["devices"] = DeviceSerializer(instance.devices, many=True).data
        return data

    class Meta:
        model = Room
        fields = (
            "id",
            "created_at",
            "room_number",
            "floor",
            "block",
            "state",
            "public_area_id",
            "pan_id",
            "building",
            "door_lock_id",
            "type",
            "suite",
            "tenant",
        )


class RoomFilterParams(ValidatorSerializer):
    SORT_FIELDS = ("room_number", "floor", "block", "device", "-room_number", "-floor", "-block", "-device")

    page = serializers.IntegerField(default=1)
    size = serializers.IntegerField(default=50)
    state = serializers.ChoiceField(choices=Room.STATE, default=Room.Available)
    search_field = serializers.ChoiceField(choices=("room_number", "floor", "block"), required=False)
    search_value = serializers.CharField(required=False)
    sort_by = serializers.ListField(child=serializers.ChoiceField(choices=SORT_FIELDS), required=False)

    def validate(self, attrs):
        if not "search_field" in attrs and "search_value" in attrs:
            raise serializers.ValidationError({"search_field": "search_field is required!"})

        if not "search_value" in attrs and "search_field" in attrs:
            raise serializers.ValidationError({"search_value": "search_value is required!"})
        return attrs
