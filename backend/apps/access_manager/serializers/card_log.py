from rest_framework import serializers

from access_manager.models import CardLog
from core.utils.serializers import ValidatorSerializer


class CardLogSerializer(serializers.ModelSerializer):
    user_id = serializers.SerializerMethodField()
    user_name = serializers.SerializerMethodField()
    user_type = serializers.SerializerMethodField()
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


class CardLogFilterParams(ValidatorSerializer):
    room = serializers.CharField()
    sort_by = serializers.ListField(
        child=serializers.ChoiceField(choices=["-event_ts", "event_ts"], default="-ts", required=False)
    )
    size = serializers.IntegerField(default=50, max_value=200)
    page = serializers.IntegerField(default=1, min_value=1)
    filters = serializers.DictField(
        required=False,
        child=serializers.DateTimeField()
    )
