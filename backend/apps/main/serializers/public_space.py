import logging

from rest_framework import serializers

from core.utils.serializers import ValidatorSerializer
from main.models import Device, DevicePublicSpaces, PublicSpace
from main.serializers.dashboard import SimpleDashboardSerializer
from main.serializers.device import SimpleDeviceSerializer

logger = logging.getLogger(__name__)


class SimplePublicSpaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PublicSpace
        fields = ("id", "name", "floor", "block")


class PublicSpaceSerializer(serializers.ModelSerializer):
    devices = serializers.SerializerMethodField(read_only=True)
    device_ids = serializers.PrimaryKeyRelatedField(
        queryset=Device.objects.all(), many=True, required=False, write_only=True
    )

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["dashboard"] = SimpleDashboardSerializer(instance.dashboard).data if instance.dashboard else None
        return data

    def get_devices(self, obj):
        if hasattr(obj, "prefetched_devices"):
            devices = [device_public_space.device for device_public_space in obj.prefetched_devices]
        else:
            devices = Device.objects.filter(device_public_spaces__public_space=obj)

        return SimpleDeviceSerializer(devices, many=True).data

    def update(self, instance, validated_data):
        device_ids = validated_data.pop("device_ids", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if device_ids is not None:
            device_public_space = DevicePublicSpaces.objects.filter(public_space=instance)
            public_space_devices = device_public_space.values_list("device_id", flat=True)
            to_remove = public_space_devices.exclude(device_id__in=device_ids)
            DevicePublicSpaces.objects.filter(device_id__in=to_remove).delete()

            public_space_devices = [str(device) for device in public_space_devices]
            new_devices = [device_id for device_id in device_ids if str(device_id.id) not in public_space_devices]
            DevicePublicSpaces.objects.bulk_create(
                [DevicePublicSpaces(device=device, public_space=instance) for device in new_devices]
            )
            self._register_cards_for_public_space(instance.id, new_devices)

        return instance

    def create(self, validated_data):
        device_ids = validated_data.pop("device_ids", [])
        instance = PublicSpace.objects.create(**validated_data)

        if device_ids:
            DevicePublicSpaces.objects.bulk_create(
                [DevicePublicSpaces(device=device, public_space=instance) for device in device_ids]
            )
            self._register_cards_for_public_space(instance.id, device_ids)

        return instance

    def _register_cards_for_public_space(self, public_space_id, new_devices):
        from access_manager.models import GroupPublicSpace
        from access_manager.tasks import card_public_space

        try:
            group_public_spaces = GroupPublicSpace.objects.filter(
                public_space_id=public_space_id, group__is_active=True
            ).select_related("group")

            for group_public_space in group_public_spaces:
                try:
                    card_public_space(
                        group_id=group_public_space.group_id,
                        public_space_id=public_space_id,
                        devices=new_devices,
                        action="connect",
                    )
                except Exception as e:
                    logger.error(
                        "Error registering cards for group %s to public space %s: %s",
                        group_public_space.group_id,
                        public_space_id,
                        str(e),
                    )

        except Exception as e:
            logger.error("Error in _register_cards_for_public_space for public space %s: %s", public_space_id, str(e))

    class Meta:
        model = PublicSpace
        fields = (
            "id",
            "created_at",
            "created_by",
            "name",
            "floor",
            "block",
            "accessible_for_guest",
            "device_ids",
            "devices",
            "tenant",
            "dashboard",
            "additional_info",
        )


class PublicSpaceFilterParams(ValidatorSerializer):
    SORT_FIELDS = ("name", "-name")

    page = serializers.IntegerField(default=1)
    size = serializers.IntegerField(default=50)
    search_field = serializers.ChoiceField(choices=(["name"]), required=False)
    search_value = serializers.CharField(required=False)
    accessible_for_guest = serializers.BooleanField(required=False, allow_null=True, default=None)
    sort_by = serializers.ListField(child=serializers.ChoiceField(choices=SORT_FIELDS), required=False)
