from rest_framework import serializers

from core.utils.serializers import ValidatorSerializer
from main.models import RoomType
from main.serializers.dashboard import SimpleDashboardSerializer


class RoomTypeSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["dashboard"] = SimpleDashboardSerializer(instance.dashboard).data if instance.dashboard else None
        return data

    class Meta:
        model = RoomType
        fields = ("id", "title", "check_in_out_address", "check_in_value", "check_out_value", "dashboard", "tenant")


class RoomTypeFilterParams(ValidatorSerializer):
    page = serializers.IntegerField(default=1)
    size = serializers.IntegerField(default=50)
    search_field = serializers.ChoiceField(choices=("title",), required=False)
    search_value = serializers.CharField(required=False)
