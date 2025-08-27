from rest_framework import serializers

from access_manager.models import CardLog
from core.utils.serializers import ValidatorSerializer


class CardLogSerializer(serializers.ModelSerializer):
    user_id = serializers.SerializerMethodField()
    user_name = serializers.SerializerMethodField()
    user_type = serializers.SerializerMethodField()
    room_number = serializers.SerializerMethodField()
    public_spaces = serializers.SerializerMethodField()
    access_group = serializers.CharField(source='get_access_group_display', read_only=True)
    device_name = serializers.CharField(source='device.name', read_only=True)

    class Meta:
        model = CardLog
        fields = [
            'event_ts',
            'number',
            'access_group',
            'device_id',
            'device_name',
            'room_number',
            'public_spaces',
            'user_id',
            'user_name',
            'user_type',
        ]

    def get_user_id(self, obj):
        if obj.guest:
            return obj.guest.id
        elif obj.staff:
            return obj.staff.id
        return None

    def get_user_name(self, obj):
        if obj.guest:
            return f"{obj.guest.name} {obj.guest.lastname}"
        elif obj.staff:
            return obj.staff.get_name()
        return None

    def get_user_type(self, obj):
        if obj.guest:
            return 'Guest'
        elif obj.staff:
            return 'Staff'
        return None

    def get_room_number(self, obj):
        # Return the room number if device is linked to a room
        if obj.device and obj.device.room:
            return obj.device.room.number
        return None

    def get_public_spaces(self, obj):
        # Return a list of connected public space names
        if obj.device:
            return [
                dps.public_space.name
                for dps in obj.device.device_public_spaces.select_related('public_space')
            ]
        return []


class CardLogFilterParams(ValidatorSerializer):
    room = serializers.CharField(required=False)
    public_space = serializers.CharField(required=False)
    user = serializers.CharField(required=False, help_text="User ID (can be guest or staff)")
    card_num = serializers.CharField(required=False, help_text="Card number to filter by")
    sort_by = serializers.ListField(
        child=serializers.ChoiceField(choices=["-event_ts", "event_ts"], default="-event_ts", required=False), required=False
    )
    size = serializers.IntegerField(default=50, max_value=200)
    page = serializers.IntegerField(default=1, min_value=1)
    filters = serializers.DictField(
        required=False,
        child=serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", input_formats=["%Y-%m-%d %H:%M:%S"])
    )
    device_ids = serializers.ListField(child=serializers.CharField(), required=False)
    room_ids = serializers.ListField(child=serializers.CharField(), required=False)
    public_space_ids = serializers.ListField(child=serializers.CharField(), required=False)
