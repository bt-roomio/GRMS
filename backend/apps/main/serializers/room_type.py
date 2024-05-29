from rest_framework import serializers

from core.utils.serializers import ValidatorSerializer
from main.models import RoomType


class RoomTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomType
        fields = ("id", "title", "check_in_out_address", "check_in_value", "check_out_value")


class RoomTypeFilterParams(ValidatorSerializer):
    page = serializers.IntegerField(default=1)
    size = serializers.IntegerField(default=50)
    search = serializers.CharField(max_length=255, required=False)
