from access_manager.models import Staff

from rest_framework import serializers

from core.utils.serializers import ValidatorSerializer


class StaffSerializer(serializers.ModelSerializer):
    is_active = serializers.BooleanField(default=True, read_only=True)

    class Meta:
        model = Staff
        fields = ("id", "created_at", "created_by", "first_name", "last_name", "is_active", "tenant", "additional_info")


class StaffFilterParams(ValidatorSerializer):
    SORT_FIELDS = ("first_name", "-first_name", "last_name", "-last_name")

    page = serializers.IntegerField(default=1)
    size = serializers.IntegerField(default=50)
    search_field = serializers.ChoiceField(choices=("first_name", "last_name"), required=False)
    search_value = serializers.CharField(required=False)
    sort_by = serializers.ListField(child=serializers.ChoiceField(choices=SORT_FIELDS), required=False)
