import logging

from hoteza.utils.exception import JsonValidationError

from rest_framework import serializers

from main.models import Guest, Room, Tenant
from main.serializers.guest import GuestSerializer

logger = logging.getLogger(__name__)


class CheckInSerializer(serializers.Serializer):
    hotelId = serializers.CharField(required=False)
    tenantId = serializers.CharField(required=False)
    roomNumber = serializers.CharField()
    guestName = serializers.CharField()
    guestFirstName = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    guestTitle = serializers.CharField(allow_null=True, allow_blank=True)
    pmsRegNum = serializers.CharField()
    arrivalDateTS = serializers.CharField()
    departureDateTS = serializers.CharField()
    guestLanguage = serializers.CharField()
    roomShare = serializers.CharField()
    swapFlag = serializers.CharField()
    nopost = serializers.CharField()
    profileNum = serializers.CharField(allow_null=True, allow_blank=True)

    def validate_arrivalDateTS(self, value):
        try:
            value = int(value)
            return value / 1000 if value > 1e12 else value
        except Exception:
            raise JsonValidationError({"result": 9, "message": "Invalid arrivalDateTS format!"})

    def validate_departureDateTS(self, value):
        try:
            value = int(value)
            return value / 1000 if value > 1e12 else value
        except Exception:
            raise JsonValidationError({"result": 9, "message": "Invalid departureDateTS format!"})

    @staticmethod
    def convert_fields(attrs):
        ret = {
            "hotelId": "hotel_id",
            "tenantId": "tenant_id",
            "guestFirstName": "name",
            "guestName": "lastname",
            "roomNumber": "room_number",
            "arrivalDateTS": "check_in",
            "departureDateTS": "check_out",
            "guestTitle": "title",
            "pmsRegNum": "pms_reg_num",
            "guestLanguage": "language",
            "roomShare": "room_share",
            "swapFlag": "swap_flag",
            "nopost": "no_post",
            "profileNum": "profile_num",
        }
        return {ret[key]: value for key, value in attrs.items() if key in ret}

    def validate(self, attrs):
        logger.debug(f"CheckInSerializer validate called with attrs: {attrs}")
        attrs = self.convert_fields(attrs)
        tenant = None
        if attrs.get("hotel_id"):
            tenant = Tenant.objects.filter(
                additional_info__integration_settings__hoteza__hotel_id=attrs.get("hotel_id"),
                additional_info__integration_settings__hoteza__enable=True,
            ).first()

        if not tenant and attrs.get("tenant_id"):
            tenant = Tenant.objects.filter(id=attrs.get("tenant_id")).first()

        if not tenant:
            raise JsonValidationError({"result": 9, "message": "Tenant not found!"})

        room = Room.objects.filter(tenant=tenant, number=attrs["room_number"]).first()
        if not room:
            raise JsonValidationError({"result": 9, "message": "Room not found!"})

        guest = Guest.objects.filter(
            additional_info__pms_reg_num=attrs.get("pms_reg_num"),
            is_active=True,
        ).first()
        logger.debug(f"Existing guest found: {guest}")

        if guest:
            # Check if any changes are needed, we need update existing guest
            has_changes = False

            # Compare basic fields
            if guest.name != attrs.get("name"):
                has_changes = True
            if guest.lastname != attrs.get("lastname"):
                has_changes = True
            if guest.room_id != room.id:
                has_changes = True
            if str(guest.check_in) != str(attrs.get("check_in")):
                has_changes = True
            if str(guest.check_out) != str(attrs.get("check_out")):
                has_changes = True
            if guest.language != attrs.get("language"):
                has_changes = True
            if guest.title != attrs.get("title"):
                has_changes = True

            # Compare additional_info fields
            guest_additional_info = guest.additional_info or {}
            if guest_additional_info.get("room_share") != attrs.get("room_share"):
                has_changes = True
            if guest_additional_info.get("swap_flag") != attrs.get("swap_flag"):
                has_changes = True
            if guest_additional_info.get("no_post") != attrs.get("no_post"):
                has_changes = True
            if guest_additional_info.get("profile_num") != attrs.get("profile_num"):
                has_changes = True

            if has_changes:
                attrs["existing_guest"] = guest
            else:
                raise JsonValidationError(
                    {"result": 0, "message": "Guest already exists with same data, no update needed."}
                )

        room.additional_info = {"swap_flag": attrs.get("swap_flag")}
        room.save()

        attrs["tenant"] = tenant
        attrs["room"] = room
        return attrs

    def create(self, validated_data):
        existing_guest = validated_data.pop("existing_guest", None)
        guest_serializer = GuestSerializer()

        if existing_guest:
            try:
                existing_additional_info = existing_guest.additional_info or {}
                del validated_data["tenant"]
                room = validated_data.pop("room")
                existing_additional_info.update(validated_data)

                instance = guest_serializer.update(
                    existing_guest,
                    {
                        "lastname": validated_data.pop("lastname"),
                        "name": validated_data.pop("name"),
                        "check_in": validated_data.pop("check_in"),
                        "check_out": validated_data.pop("check_out"),
                        "room": room,
                        "language": validated_data.pop("language"),
                        "title": validated_data.pop("title"),
                        "additional_info": existing_additional_info,
                    },
                )
            except Exception as e:
                logger.error(f"Error updating guest: {e}")
                raise JsonValidationError({"result": 9, "message": "Failed to update guest."})
        else:
            logger.debug("Creating new guest with data: %s", validated_data)
            # Create new guest
            try:
                instance = guest_serializer.create(
                    {
                        "lastname": validated_data.pop("lastname"),
                        "name": validated_data.pop("name"),
                        "check_in": validated_data.pop("check_in"),
                        "check_out": validated_data.pop("check_out"),
                        "auto_check_out": True,
                        "room": validated_data.pop("room"),
                        "language": validated_data.pop("language"),
                        "title": validated_data.pop("title"),
                        "tenant": validated_data.pop("tenant"),
                        "additional_info": validated_data,
                    }
                )
            except Exception as e:
                logger.error(f"Error creating guest: {e}")
                raise JsonValidationError({"result": 9, "message": "Failed to create guest."})
        logger.info(f"Guest check-in processed: {instance.name}")  # pyright: ignore
        return instance
