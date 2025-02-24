from access_manager.models import Card, Staff, StaffCard
from access_manager.serializers.staff import SimpleStaffSerializer

from rest_framework import serializers
from rest_framework.fields import ValidationError

from core.utils.serializers import ValidatorSerializer


class CardSerializer(serializers.ModelSerializer):
    staff_id = serializers.PrimaryKeyRelatedField(write_only=True, queryset=Staff.objects.all(), required=False)
    staff = SimpleStaffSerializer(source="staffcard.staff", read_only=True)

    def create(self, validated_data):
        staff = validated_data.pop("staff_id") if validated_data.get("staff_id") else None
        instance = super().create(validated_data)
        try:
            if staff:
                StaffCard.objects.create(card=instance, staff=staff)
        except Exception as err:
            raise ValidationError(str(err))
        return instance

    def update(self, instance, validated_data):
        staff = validated_data.pop("staff_id") if validated_data.get("staff_id") else None
        if staff:
            StaffCard.objects.filter(card=instance).delete()
            StaffCard.objects.create(card=instance, staff=staff)
        return super().update(instance, validated_data)

    class Meta:
        model = Card
        fields = (
            "id",
            "created_at",
            "created_by",
            "number",
            "tenant",
            "staff",
            "staff_id",
            "additional_info",
        )


class CardFilterParams(ValidatorSerializer):
    SORT_FIELDS = ("name", "-name")

    page = serializers.IntegerField(default=1)
    size = serializers.IntegerField(default=50)
    search_field = serializers.ChoiceField(choices=("name"), required=False)
    search_value = serializers.CharField(required=False)
    sort_by = serializers.ListField(child=serializers.ChoiceField(choices=SORT_FIELDS), required=False)
