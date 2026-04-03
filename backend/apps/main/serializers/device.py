import logging

from access_manager.models import NeedSyncDevice

from rest_framework import serializers

from core.utils.random_letter import get_random_letter
from core.utils.serializers import ValidatorSerializer
from main.models import Device, DeviceCredentials, DeviceProfile, Tenant
from main.serializers.device_credentials import DeviceCredentialsSerializer
from main.serializers.device_profile import SimpleDeviceProfileSerializer
from main.utils.has_roomio_node import has_roomio_node

logger = logging.getLogger(__name__)


class SimpleDeviceSerializer(serializers.ModelSerializer):
    public_spaces = serializers.SerializerMethodField()
    room_obj = serializers.SerializerMethodField()
    need_sync = serializers.SerializerMethodField()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["device_profile"] = str(instance.device_profile_id)
        data["tenant"] = str(instance.tenant_id)
        data["room"] = str(instance.room_id) if instance.room_id else None
        return data

    def get_public_spaces(self, obj):
        public_spaces = [dps.public_space.name for dps in getattr(obj, "prefetched_device_public_spaces", [])]
        return public_spaces

    def get_room_obj(self, obj):
        from main.serializers.room import SimpleRoomSerializer

        if self.context.get("exclude_room_obj", True):
            return None
        if obj.room:
            return SimpleRoomSerializer(obj.room).data
        return None

    def get_need_sync(self, obj):
        if hasattr(obj, "need_sync"):
            return obj.need_sync
        if self.context.get("need_sync", False):
            return NeedSyncDevice.objects.filter(device=obj, need_sync=True).exists()
        return None

    class Meta:
        model = Device
        fields = (
            "id",
            "created_at",
            "name",
            "status",
            "type",
            "tenant",
            "room",
            "room_obj",
            "device_profile",
            "label",
            "additional_info",
            "device_data",
            "public_spaces",
            "external_id",
            "need_sync",
        )


class DeviceSerializer(serializers.ModelSerializer):
    tenant = serializers.PrimaryKeyRelatedField(queryset=Tenant.objects.all(), required=False)
    credentials = serializers.PrimaryKeyRelatedField(queryset=DeviceCredentials.objects.all(), required=False)
    public_spaces = serializers.SerializerMethodField(read_only=True)
    as_door_lock_room = serializers.UUIDField(read_only=True)

    def to_representation(self, instance):
        from main.serializers.room import SimpleRoomSerializer

        data = super().to_representation(instance)
        data["credentials"] = (
            DeviceCredentialsSerializer(instance=instance.credentials).data
            if hasattr(instance, "credentials")
            else None
        )
        data["device_profile"] = SimpleDeviceProfileSerializer(instance.device_profile).data
        data["room"] = SimpleRoomSerializer(instance.room).data if instance.room_id else None
        return data

    def get_public_spaces(self, instance):
        from main.serializers.public_space import SimplePublicSpaceSerializer

        rel_mgr = getattr(instance, "device_public_spaces", None)
        if rel_mgr is None:
            return []
        qs = rel_mgr.select_related("public_space")
        return [SimplePublicSpaceSerializer(space.public_space).data for space in qs]

    def create(self, validated_data):
        if validated_data.get("additional_info", {}).get("roomio_node") and has_roomio_node(
            validated_data.get("tenant_id")
        ):
            raise serializers.ValidationError({"detail": "You already have a device with a 'roomio_node'."})

        instance = super().create(validated_data)
        DeviceCredentials.objects.create(
            device=instance,
            credentials_id=get_random_letter(32),
            credentials_type="ACCESS_TOKEN",
        )
        return instance

    def update(self, instance, validated_data):
        if validated_data.get("additional_info", {}).get("roomio_node") and has_roomio_node(
            validated_data.get("tenant_id"), instance.id
        ):
            raise serializers.ValidationError({"detail": "You already have a device with a 'roomio_node'."})

        old_room_id = instance.room_id if instance.pk else None

        updated_instance = super().update(instance, validated_data)

        new_room_id = updated_instance.room_id

        if old_room_id != new_room_id and new_room_id and updated_instance.is_active and updated_instance.status:
            self._register_cards_for_room(new_room_id)

        return updated_instance

    def _register_cards_for_room(self, room_id):
        from access_manager.models import GroupRoom
        from access_manager.utilits.task_trigger import card_room

        try:
            group_rooms = GroupRoom.objects.filter(room_id=room_id, group__is_active=True).select_related("group")
            for group_room in group_rooms:
                try:
                    card_room(group_id=group_room.group_id, room_id=room_id, action="connect")
                except Exception as e:
                    logger.error(
                        "Error registering cards for group %s to room %s: %s", group_room.group_id, room_id, str(e)
                    )

        except Exception as e:
            logger.error("Error in _register_cards_for_room for room %s: %s", room_id, str(e))

    class Meta:
        model = Device
        fields = (
            "id",
            "created_at",
            "name",
            "status",
            "type",
            "tenant",
            "customer",
            "room",
            "as_door_lock_room",
            "public_spaces",
            "device_profile",
            "label",
            "additional_info",
            "device_data",
            "external_id",
            "credentials",
        )


class DeviceFilterParams(ValidatorSerializer):
    SORT_FIELDS = (
        "created_at",
        "-created_at",
        "name",
        "-name",
        "status",
        "-status",
        "device_profile",
        "-device_profile",
        "gateway",
        "-gateway",
    )

    page = serializers.IntegerField(default=1)
    size = serializers.IntegerField(default=50)
    search_field = serializers.ChoiceField(choices=("name", "device_profile__name", "label"), required=False)
    search_value = serializers.CharField(required=False)
    name = serializers.CharField(required=False)
    status = serializers.BooleanField(allow_null=True, required=False)
    device_profile = serializers.UUIDField(required=False)
    sort_by = serializers.ListField(child=serializers.ChoiceField(choices=SORT_FIELDS), required=False)


class DeviceQuickFilterParams(DeviceFilterParams):
    page = None
    size = None
    name = None
    status = None
    device_profile = serializers.CharField(required=False)
    search_field = None
    sort_by = None


class GatewayListSerializer(serializers.ModelSerializer):
    total_connectors = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = Device
        fields = ("id", "name", "total_connectors", "status")

    def _attrs(self, obj: Device) -> dict:
        return {a.attribute_key: a for a in obj.attribute_kvs.all()}

    def get_total_connectors(self, obj: Device) -> int:
        m = self._attrs(obj)
        a = (m.get("active_connectors") or {}).get_value if m.get("active_connectors") else []
        i = (m.get("inactive_connectors") or {}).get_value if m.get("inactive_connectors") else []
        return len(a or []) + len(i or [])

    def get_status(self, obj: Device) -> bool:
        m = self._attrs(obj)
        v = m.get("active").get_value if m.get("active") else False
        if isinstance(v, str):
            return v.strip().lower() in {"1", "true", "yes", "on"}
        return bool(v)
