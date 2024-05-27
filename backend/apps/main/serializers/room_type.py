from rest_framework import serializers

from main.models import RoomType


class RoomTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomType
        fields = (
            "id",
            "title",
            "active",
            "check_in_out_address",
            "check_in_value",
            "check_out_value",
            "tenant",
        )
