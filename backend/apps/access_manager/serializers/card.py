from access_manager.models import Card, GuestCard, NeedSyncDevice, Staff, StaffCard
from access_manager.serializers.staff import SimpleStaffSerializer
from access_manager.tasks.send_rpc import send_rpc_request

from rest_framework import serializers
from rest_framework.fields import ValidationError

from core.utils.serializers import ValidatorSerializer
from main.models import Guest
from main.utils.access_context import get_guest_access_context


class CardSerializer(serializers.ModelSerializer):
    staff_id = serializers.PrimaryKeyRelatedField(
        write_only=True, queryset=Staff.objects.all(), required=False
    )
    staff = SimpleStaffSerializer(source="staffcard.staff", read_only=True)
    need_sync = serializers.SerializerMethodField()

    def get_need_sync(self, card):
        return NeedSyncDevice.objects.filter(card=card, need_sync=True).exists()

    def create(self, validated_data):
        staff = (
            validated_data.pop("staff_id") if validated_data.get("staff_id") else None
        )
        instance = super().create(validated_data)
        try:
            if staff:
                StaffCard.objects.create(card=instance, staff=staff)
        except Exception as err:
            raise ValidationError(str(err))
        return instance

    def update(self, instance, validated_data):
        staff = (
            validated_data.pop("staff_id") if validated_data.get("staff_id") else None
        )
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
            "is_pwd",
            "additional_info",
            "need_sync",
        )


class CardFilterParams(ValidatorSerializer):
    SORT_FIELDS = ("number", "-number")

    page = serializers.IntegerField(default=1)
    size = serializers.IntegerField(default=50)
    search_field = serializers.ChoiceField(choices=("number",), required=False)
    search_value = serializers.CharField(required=False)
    sort_by = serializers.ListField(
        child=serializers.ChoiceField(choices=SORT_FIELDS), required=False
    )
    staff_id = serializers.CharField(required=False)
    is_pwd = serializers.BooleanField(required=False, allow_null=True, default=None)


class DisconnectCardSerializer(serializers.Serializer):
    card_id = serializers.CharField()

    def create(self, validated_data):
        try:
            card = GuestCard.objects.select_related("card", "guest").get(
                card_id=validated_data["card_id"], is_active=True
            )
            deactivate_results = []
            guest = Guest.objects.filter(id=card.guest.id).first()
            access_context = get_guest_access_context(guest)
            devices = access_context.get("devices", [])
            card_number = [card.card.number]
            is_pwd = bool(card.card.is_pwd)
            for device in devices:
                deactivate_result = send_rpc_request(
                    str(device.id), card_number, 0, is_pwd=is_pwd
                )
                deactivate_results.append(deactivate_result)
            if any(not r.get("success", False) for r in deactivate_results):
                return {
                    "success": False,
                    "message": "Card is not deactivated from some devices !",
                    "results": deactivate_results,
                }
            return {"success": True, "message": "Card is deactivated !"}
        except GuestCard.DoesNotExist:
            return {"success": False, "message": "Active guest card not found !"}
