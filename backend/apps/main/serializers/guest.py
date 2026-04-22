import logging

from access_manager.tasks.send_rpc import send_rpc_request

from rest_framework import serializers

from core.utils.helpers import safely_remove
from core.utils.serializers import ValidatorSerializer
from main.models import Guest, Room
from main.utils.access_context import get_guest_access_context

logger = logging.getLogger(__name__)


class SimpleGuestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Guest
        fields = ("id", "name", "lastname")


class GuestMoveRoomFilterParams(ValidatorSerializer):
    from_room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all())
    to_room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all())


class GuestMoveRoomSerializer(serializers.Serializer):
    to_room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all())
    from_room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all())

    def update(self, instance, validated_data):
        from_room = validated_data.pop("from_room")
        from_room.save(update_fields=["state"])

        for guest in instance:
            guest.room = validated_data.get("to_room")
            guest.save()

        to_room = validated_data.pop("to_room")
        to_room.save(update_fields=["state"])

        return instance


class GuestSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["room"] = str(instance.room_id) if instance.room_id else None
        return data

    def validate_room(self, value):
        tenant_id = self.context.get("tenant_id")
        if value and value.tenant_id != tenant_id:
            raise serializers.ValidationError("Room does not found.")
        return value

    def create(self, validated_data):
        try:
            instance = super().create(validated_data)
            room = instance.room
            if room:
                # room.state = safely_remove(room.state, Room.Available)
                # room.state.append(Room.CheckedIn)
                room.save(update_fields=["state"])
            return instance
        except Exception as e:
            logger.warning(e)
            raise e

    def update(self, instance: Guest, validated_data):
        logger.info(f"Updating Guest {instance.id} with data: {validated_data}")
        deactivate_result = {"success": True}

        access_context = get_guest_access_context(instance)

        old_room = instance.room_id and Room.objects.prefetch_related("guests").filter(id=instance.room_id).first()
        if old_room and len(old_room.guests.all()) == 1:  # pyright: ignore
            old_room.state = safely_remove(old_room.state, Room.Available)
            old_room.save(update_fields=["state"])

        new_room = validated_data.get("room") and Room.objects.filter(id=validated_data.get("room").id).first()
        if new_room and not new_room.guests.exists():  # pyright: ignore
            # new_room.state = [Room.CheckedIn]
            new_room.save(update_fields=["state"])

        new_checkout = validated_data.get("check_out")
        if new_checkout and new_checkout > instance.check_out:
            blocked_guest_cards = access_context.get("blocked_guest_cards")
            if blocked_guest_cards:
                for device in access_context.get("devices"):
                    _ = send_rpc_request(
                        str(device.id), access_context.get("blocked_cards"), 1, guest_id=str(instance.id)
                    )
                blocked_guest_cards.update(is_blocked=False)

        room_to_update = None
        if "is_reservation" in validated_data:
            room_to_update = instance.room

        if isinstance(validated_data.get("is_active"), bool) and not validated_data.get("is_active"):
            logger.info(f"Deactivating Guest {instance.id}")
            room = instance.room
            devices = access_context.get("devices")
            cards = access_context.get("cards")
            for device in devices:
                result = send_rpc_request(str(device.id), cards, 0, guest_id=str(instance.id))
                not result.get("success") and deactivate_result.update({"success": False})  # pyright: ignore

            if room and len(room.guests.filter(is_active=True, is_reservation=False)) <= 1:  # pyright: ignore
                room_to_update = room

            self._deactivate_result = deactivate_result
            instance.checkout_by = instance.CHECKOUT_BY.ROOMIO

        updated = super().update(instance, validated_data)

        if room_to_update:
            logger.info(f"Updating Room {room_to_update.id} state to Available")
            room_to_update.save(update_fields=["state"])
            self.context["deactivate_results"] = deactivate_result

        return updated

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
            "is_reservation",
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
            "is_reservation": {"default": True},
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
    room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all(), required=False)
    sort_by = serializers.ListField(child=serializers.ChoiceField(choices=SORT_FIELDS), default=[], required=False)
    room_state = serializers.ChoiceField(choices=(Room.CHECKEDIN, Room.RESERVED), default=Room.CHECKEDIN)

    def validate(self, attrs):
        STATE_MAP = {name: num for num, name in Room.STATE}

        if "room_state" in attrs:
            attrs["room_state"] = STATE_MAP[attrs["room_state"]]
        return super().validate(attrs)


class GuestQuickFilterParams(GuestFilterParams):
    page = None
    size = None
    sort_by = None
    search_field = None
    search_value = serializers.CharField(required=False)


class GuestCheckoutParams(ValidatorSerializer):
    room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all())
