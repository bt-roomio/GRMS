from access_manager.models import Group, GroupStaff, Staff
from access_manager.serializers.group import SimpleGroupSerializer

from rest_framework import serializers
from rest_framework.fields import ValidationError

from core.utils.serializers import ValidatorSerializer


class SimpleStaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = Staff
        fields = ("id", "first_name", "last_name")


class StaffSerializer(serializers.ModelSerializer):
    is_active = serializers.BooleanField(default=True, read_only=True)
    group_id = serializers.PrimaryKeyRelatedField(write_only=True, queryset=Group.objects.all(), required=False)
    group = SimpleGroupSerializer(source="groupstaff.group", read_only=True)

    def create(self, validated_data):
        group = validated_data.pop("group_id") if validated_data.get("group_id") else None
        instance = super().create(validated_data)
        try:
            if group:
                GroupStaff.objects.create(staff=instance, group=group)
        except Exception as err:
            raise ValidationError(str(err))
        return instance

    def update(self, instance, validated_data):
        group = validated_data.pop("group_id") if validated_data.get("group_id") else None
        if group:
            GroupStaff.objects.filter(staff=instance).delete()
            GroupStaff.objects.create(staff=instance, group=group)
        return super().update(instance, validated_data)

    class Meta:
        model = Staff
        fields = (
            "id",
            "created_at",
            "created_by",
            "first_name",
            "last_name",
            "group_id",
            "group",
            "is_active",
            "tenant",
            "additional_info",
        )


class StaffFilterParams(ValidatorSerializer):
    SORT_FIELDS = ("first_name", "-first_name", "last_name", "-last_name")

    page = serializers.IntegerField(default=1)
    size = serializers.IntegerField(default=50)
    search_field = serializers.ChoiceField(choices=("first_name", "last_name"), required=False)
    search_value = serializers.CharField(required=False)
    sort_by = serializers.ListField(child=serializers.ChoiceField(choices=SORT_FIELDS), required=False)
