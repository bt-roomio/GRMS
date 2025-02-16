from access_manager.models import Group

from rest_framework import serializers

from core.utils.serializers import ValidatorSerializer
from users.serializers.user import SimpleUserSerializer


class SimpleGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ("id", "name")


class GroupSerializer(serializers.ModelSerializer):
    is_active = serializers.BooleanField(default=True, read_only=True)
    created_by = SimpleUserSerializer(read_only=True)

    class Meta:
        model = Group
        fields = (
            "id",
            "created_at",
            "created_by",
            "name",
            "tenant",
            "week_days",
            "start_time",
            "end_time",
            "expiry_date",
            "is_active",
            "additional_info",
        )


class GroupFilterParams(ValidatorSerializer):
    SORT_FIELDS = (
        "name",
        "-name",
        "start_time",
        "-start_time",
        "end_time",
        "-end_time",
        "expiry_date",
        "-expiry_date",
        "created_by",
        "-created_by",
    )

    page = serializers.IntegerField(default=1)
    size = serializers.IntegerField(default=50)
    search_field = serializers.ChoiceField(choices=("name", "expiry_data"), required=False)
    search_value = serializers.CharField(required=False)
    sort_by = serializers.ListField(child=serializers.ChoiceField(choices=SORT_FIELDS), required=False)
