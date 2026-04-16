from access_manager.models import Group, Staff, StaffCard
from access_manager.serializers.group import SimpleGroupSerializer
from access_manager.serializers.staff_card import StaffCardSerializer

from rest_framework import serializers

from core.utils.serializers import ValidatorSerializer


class SimpleStaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = Staff
        fields = ("id", "first_name", "last_name")


class StaffSerializer(serializers.ModelSerializer):
    is_active = serializers.BooleanField(default=True, read_only=True)
    group = serializers.PrimaryKeyRelatedField(queryset=Group.objects.all(), allow_null=True)
    cards = serializers.SerializerMethodField()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["group"] = SimpleGroupSerializer(instance.group).data if instance.group else None
        return data

    def get_cards(self, obj):
        staff_cards = StaffCard.objects.filter(staff=obj, is_active=True).select_related("card")
        return StaffCardSerializer(staff_cards, many=True).data

    class Meta:
        model = Staff
        fields = (
            "id",
            "created_at",
            "created_by",
            "first_name",
            "last_name",
            "group",
            "is_active",
            "tenant",
            "cards",
            "additional_info",
        )


class StaffFilterParams(ValidatorSerializer):
    SORT_FIELDS = ("first_name", "-first_name", "last_name", "-last_name")

    page = serializers.IntegerField(default=1)
    size = serializers.IntegerField(default=50)
    search_field = serializers.ChoiceField(choices=("first_name", "last_name"), required=False)
    search_value = serializers.CharField(required=False)
    sort_by = serializers.ListField(child=serializers.ChoiceField(choices=SORT_FIELDS), required=False)
    in_group = serializers.PrimaryKeyRelatedField(queryset=Group.objects.all(), required=False)
    not_in_group = serializers.PrimaryKeyRelatedField(queryset=Group.objects.all(), required=False)


class StaffQuickFilterParams(StaffFilterParams):
    page = None
    size = None
    sort_by = None
    in_group = None
    not_in_group = None
    search_field = None
