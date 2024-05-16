from rest_framework import serializers

from core.utils.serializers import ValidatorSerializer
from main.models import Room, Tenant


class RoomSerializer(serializers.ModelSerializer):
    tenant = serializers.PrimaryKeyRelatedField(queryset=Tenant.objects.all(), required=False)

    class Meta:
        model = Room
        fields = ('id', 'created_at', 'room_number', 'floor', 'block', 'status',
            'public_area_id', 'pan_id', 'building', 'door_lock_id', 'device', 'type', 'suite', 'tenant')


class RoomFilterParams(ValidatorSerializer):
    page = serializers.IntegerField(default=1)
    size = serializers.IntegerField(default=50)
