from rest_framework import serializers

from core.utils.serializers import ValidatorSerializer

MUR = "MUR Relay"
DND = "DND Relay"
AC_ON_OFF = "AC ON OFF"
Room_Temperature = "Room Temperature"
Occupancy_State = "Occupancy State"

STATIC_KEYS = {
    MUR: "MUR Relay",
    DND: "DND Relay",
    AC_ON_OFF: "AC_ON_OFF",
    Room_Temperature: "Room Temperature",
    Occupancy_State: "Occupancy State",
}


class RoomDetailWsFilterBodySerializer(ValidatorSerializer):
    pk = serializers.UUIDField(required=True, help_text="Room ID")
    keys = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="List of keys to filter the room details",
        default=list(STATIC_KEYS.keys()),
    )

    def validate_keys(self, value):
        """
        Ensures that STATIC_KEYS are always included in the keys.
        """
        if not value:
            value = []
        return list(set(value + list(STATIC_KEYS.keys())))

    request_id = serializers.CharField(required=True, help_text="Unique request ID")
