from access_manager.models import Card, Staff, StaffCard, GuestCard
from access_manager.serializers.staff import SimpleStaffSerializer

from rest_framework import serializers
from rest_framework.fields import ValidationError

from access_manager.views.guest_card import prepare_cards, prepare_mqtt_request
from core.utils.serializers import ValidatorSerializer
from main.models import Device, Guest


class CardSerializer(serializers.ModelSerializer):
    staff_id = serializers.PrimaryKeyRelatedField(write_only=True, queryset=Staff.objects.all())
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
    SORT_FIELDS = ("number", "-number")

    page = serializers.IntegerField(default=1)
    size = serializers.IntegerField(default=50)
    search_field = serializers.ChoiceField(choices=("number",), required=False)
    search_value = serializers.CharField(required=False)
    sort_by = serializers.ListField(child=serializers.ChoiceField(choices=SORT_FIELDS), required=False)


class DisconnectCardSerializer(serializers.Serializer):
    card_id = serializers.CharField()

    def create(self, validated_data):
        card = GuestCard.objects.get(card_id=validated_data["card_id"], is_active=True)

        if card:
            guest = Guest.objects.filter(id=card.guest.id).first()
            device = Device.objects.filter(room=guest.room, is_active=True).select_related("tenant").first()
            card_number = [card.card.number]
            rpc_params = prepare_cards(card_number, 0)
            deactivate_result = prepare_mqtt_request(device, rpc_params, card_number, guests=[guest], guest=None)
            return deactivate_result
        return {"success": False, "message": "Active card not found !"}
