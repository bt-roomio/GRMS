from typing import List, TypedDict

from access_manager.models import Staff, StaffCard

from rest_framework import serializers


class StaffCardRequestData(TypedDict):
    staff_id: Staff
    cards: List[str]


class StaffCardRequestSerializer(serializers.Serializer):
    staff_id = serializers.PrimaryKeyRelatedField(queryset=Staff.objects.all())
    cards = serializers.ListField(
        child=serializers.CharField(), max_length=10, error_messages={"max_length": "Maximum 10 cards allowed"}
    )

    def validate_staff_id(self, value):
        staff = Staff.objects.filter(id=value.id, tenant_id=self.context["tenant_id"]).first()
        if not staff:
            raise serializers.ValidationError("Not found staff.")
        if not staff.is_active:
            raise serializers.ValidationError("Staff is not active")
        if not staff.group:
            raise serializers.ValidationError("Staff has no group")
        return value

    def validate_cards(self, value):
        if len(value) > 10:
            raise serializers.ValidationError("Maximum 10 cards allowed")
        return value


class StaffCardSerializer(serializers.ModelSerializer):
    card_id = serializers.SerializerMethodField()
    card_number = serializers.SerializerMethodField()
    need_sync = serializers.SerializerMethodField()

    class Meta:
        model = StaffCard
        fields = ('created_at', 'card_id', 'card_number', 'need_sync')

    def get_card_id(self, obj):
        return obj.card.id

    def get_card_number(self, obj):
        return obj.card.number

    def get_need_sync(self, obj):
        from access_manager.models import NeedSyncDevice
        return NeedSyncDevice.objects.filter(
            card=obj.card,
            need_sync=True
        ).exists()
