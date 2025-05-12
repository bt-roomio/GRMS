from rest_framework import serializers

from access_manager.models import GuestCard
from access_manager.views.guest_card import prepare_cards, prepare_mqtt_request
from core.utils.helpers import safely_remove
from core.utils.serializers import ValidatorSerializer
from main.models import Guest, Room, Device


class GuestMoveRoomFilterParams(ValidatorSerializer):
    from_room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all())
    to_room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all())


class GuestMoveRoomSerializer(serializers.Serializer):
    to_room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all())
    from_room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all())

    def update(self, instance, validated_data):
        from_room = validated_data.pop("from_room")
        from_room.state.append(Room.Available)
        from_room.state = safely_remove(from_room.state, Room.CheckedIn)
        from_room.save(update_fields=["state"])

        for guest in instance:
            guest.room = validated_data.get("to_room")
            guest.save()

        to_room = validated_data.pop("to_room")
        to_room.state.append(Room.CheckedIn)
        to_room.state = safely_remove(to_room.state, Room.Available)
        to_room.save(update_fields=["state"])

        return instance


class GuestSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["room"] = str(instance.room_id) if instance.room_id else None
        return data

    def create(self, validated_data):
        instance = super().create(validated_data)

        room = instance.room
        if room:
            room.state = safely_remove(room.state, Room.Available)
            room.state.append(Room.CheckedIn)
            room.save(update_fields=["state"])
        return instance

    def update(self, instance, validated_data):
        old_room = instance.room_id and Room.objects.prefetch_related("guests").filter(id=instance.room_id).first()
        if old_room and len(old_room.guests.all()) == 1:  # pyright: ignore
            old_room.state = safely_remove(old_room.state, Room.Available)
            old_room.save(update_fields=["state"])

        new_room = validated_data.get("room") and Room.objects.filter(id=validated_data.get("room").id).first()
        if new_room and not new_room.guests.exists():  # pyright: ignore
            new_room.state = safely_remove(new_room.state, Room.Available)
            new_room.state.append(Room.CheckedIn)
            new_room.save(update_fields=["state"])

        if validated_data.get("is_active") == False:
            room = Room.objects.filter(id=instance.room_id).first()
            guests = [instance]
            cards = GuestCard.objects.filter(guest__in=guests, is_active=True).values_list("card__number", flat=True)
            device = Device.objects.filter(room__id=room.id, is_active=True).select_related("tenant").first()
            rpc_params = prepare_cards(cards, 0)
            deactivate_result = prepare_mqtt_request(device, rpc_params, cards, guests=guests, guest=None)
            if deactivate_result.get("cards_empty", False) or deactivate_result.get("success"):
                if room and len(room.guests.filter(is_active=True)) <= 1:  # pyright: ignore
                    room.state = safely_remove(room.state, Room.CheckedIn)
                    room.state.append(Room.Available)
                    room.save(update_fields=["state"])
                    return super().update(instance, validated_data)
            return deactivate_result
        return None

    class Meta:
        model = Guest
        fields = (
            "id",
            "created_at",
            "name",
            "lastname",
            "gender",
            "nationality",
            "language",
            "title",
            "birthday",
            "is_active",
            "room",
            "check_in",
            "check_out",
            "auto_check_out",
            "reservation_number",
            "additional_info",
        )
        extra_kwargs = {
            "check_in": {"required": True},
            "check_out": {"required": True},
            "is_active": {"default": True},
        }


class GuestFilterParams(ValidatorSerializer):
    SORT_FIELDS = (
        "created_at",
        "-created_at",
        "name",
        "-name",
        "lastname",
        "-lastname",
        "gender",
        "-gender",
        "nationality",
        "-nationality",
    )

    page = serializers.IntegerField(default=1)
    size = serializers.IntegerField(default=50)
    room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all())
    sort_by = serializers.ListField(child=serializers.ChoiceField(choices=SORT_FIELDS), required=False)


class GuestCheckoutParams(ValidatorSerializer):
    room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all())
